"""Step 4 — assemble the master per-H3 cell table (res 10, Uber H3).

Unions three sparse candidate-cell sources and attaches attributes + admin:
  urban   <- Google Open Buildings centroids  (data/buildings/*.csv)  via DuckDB h3
  roads   <- data/roads.parquet               (built / building, by class)
  islands <- data/admin_wards.parquet where is_island (đặc khu) polyfill

Outputs:
  data/cells.parquet       one row per res-10 cell
  data/cells_res9.parquet  res-9 rollup for zoomed-out rendering
"""
import glob
import sys
from pathlib import Path

import duckdb
import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import shape

DATA = Path(__file__).resolve().parents[1] / "data"
RES = 10
ROAD_RANK = {"primary": 1, "trunk": 2, "motorway": 3}  # higher = more strategic


# ---------------------------------------------------------------- urban
def urban_cells() -> pd.DataFrame:
    csvs = sorted(glob.glob(str(DATA / "buildings" / "*.csv")))
    if not csvs:
        print("! no building CSVs in data/buildings/ — urban layer empty")
        return pd.DataFrame(columns=["h3_id", "built_up_area_m2", "building_count"])
    con = duckdb.connect()
    con.execute("INSTALL h3 FROM community; LOAD h3;")
    df = con.execute(
        """
        SELECT h3_latlng_to_cell_string(lat, lon, ?) AS h3_id,
               SUM(area)  AS built_up_area_m2,
               COUNT(*)   AS building_count
        FROM read_csv_auto(?, union_by_name=true)
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        GROUP BY 1
        """,
        [RES, csvs],
    ).df()
    print(f"urban: {len(df):,} cells from {len(csvs)} building file(s)")
    return df


# ---------------------------------------------------------------- roads
def _line_cells(geom):
    cells = set()
    parts = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
    for ls in parts:
        dense = ls.segmentize(0.0002)  # ~22 m < res-10 edge (~65 m)
        for lng, lat in dense.coords:
            cells.add(h3.latlng_to_cell(lat, lng, RES))
    return cells


def road_cells() -> pd.DataFrame:
    g = gpd.read_parquet(DATA / "roads.parquet")
    rows = {}  # h3_id -> dict
    for cls, status, geom in zip(g["class"], g["status"], g.geometry):
        if geom is None:
            continue
        for c in _line_cells(geom):
            r = rows.setdefault(c, {"built": None, "constr": None})
            key = "built" if status == "built" else "constr"
            if r[key] is None or ROAD_RANK[cls] > ROAD_RANK[r[key]]:
                r[key] = cls
    out = pd.DataFrame([
        {"h3_id": c, "road_built": r["built"] is not None,
         "road_built_class": r["built"],
         "road_construction": r["constr"] is not None,
         "road_constr_class": r["constr"]}
        for c, r in rows.items()
    ])
    print(f"roads: {len(out):,} cells")
    return out


# ---------------------------------------------------------------- islands
def island_cells(admin: gpd.GeoDataFrame) -> pd.DataFrame:
    isl = admin[admin["is_island"]]
    cells = set()
    for geom in isl.geometry:
        for poly in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
            outer = [(lat, lng) for lng, lat in poly.exterior.coords]
            holes = [[(lat, lng) for lng, lat in r.coords] for r in poly.interiors]
            shp = h3.LatLngPoly(outer, *holes)
            cells.update(h3.polygon_to_cells(shp, RES))
    out = pd.DataFrame({"h3_id": sorted(cells)})
    out["is_island"] = True

    # land-only subset: island cells whose center falls on OSM coastline land
    land = gpd.read_parquet(DATA / "island_land.parquet")
    centers = [h3.cell_to_latlng(c) for c in out["h3_id"]]
    pts = gpd.GeoDataFrame(
        out[["h3_id"]],
        geometry=gpd.points_from_xy([p[1] for p in centers], [p[0] for p in centers]),
        crs=4326,
    )
    onland = gpd.sjoin(pts, land[["geometry"]], how="inner", predicate="within")
    out["is_island_land"] = out["h3_id"].isin(onland["h3_id"])
    print(f"islands: {len(out):,} cells ({int(out['is_island_land'].sum()):,} on land)")
    return out


# ---------------------------------------------------------------- admin join
def attach_admin(df: pd.DataFrame, admin: gpd.GeoDataFrame) -> pd.DataFrame:
    latlng = [h3.cell_to_latlng(c) for c in df["h3_id"]]
    df["lat"] = [p[0] for p in latlng]
    df["lng"] = [p[1] for p in latlng]
    pts = gpd.GeoDataFrame(
        df[["h3_id"]],
        geometry=gpd.points_from_xy(df["lng"], df["lat"]),
        crs=4326,
    )
    joined = gpd.sjoin(pts, admin[["province", "ward", "geometry"]],
                       how="left", predicate="within")
    joined = joined.drop_duplicates("h3_id").set_index("h3_id")
    df = df.set_index("h3_id")
    df["province"] = joined["province"]
    df["ward"] = joined["ward"]
    return df.reset_index()


# ---------------------------------------------------------------- main
def main() -> int:
    admin = gpd.read_parquet(DATA / "admin_wards.parquet")

    df = urban_cells().merge(road_cells(), on="h3_id", how="outer")
    df = df.merge(island_cells(admin), on="h3_id", how="outer")

    # normalise flags / fills
    df["built_up_area_m2"] = df["built_up_area_m2"].fillna(0.0)
    df["building_count"] = df["building_count"].fillna(0).astype(int)
    for col in ("road_built", "road_construction", "is_island", "is_island_land"):
        df[col] = df[col].fillna(False).astype(bool)

    df["cell_area_m2"] = [h3.cell_area(c, "m^2") for c in df["h3_id"]]
    df["built_up_ratio"] = (df["built_up_area_m2"] / df["cell_area_m2"]).clip(upper=1.0)
    df["res9_id"] = [h3.cell_to_parent(c, 9) for c in df["h3_id"]]

    df = attach_admin(df, admin)

    df.to_parquet(DATA / "cells.parquet", index=False)
    print(f"\nwrote cells.parquet: {len(df):,} cells, "
          f"{df['province'].notna().mean()*100:.1f}% with province")

    roll = df.groupby("res9_id").agg(
        built_up_area_m2=("built_up_area_m2", "sum"),
        building_count=("building_count", "sum"),
        cell_area_m2=("cell_area_m2", "sum"),
        n_cells=("h3_id", "size"),
        road_built=("road_built", "max"),
        road_construction=("road_construction", "max"),
        is_island=("is_island", "max"),
    ).reset_index()
    roll.to_parquet(DATA / "cells_res9.parquet", index=False)
    print(f"wrote cells_res9.parquet: {len(roll):,} res-9 cells")
    return 0


if __name__ == "__main__":
    sys.exit(main())
