"""Step 5 — per-H3 road-coverage sidecar for the enrichment dashboard.

Tallies, for each res-10 H3 cell, the geodesic km of tertiary+ road it contains
and how many of those km already carry maxspeed / name / lanes tags. Lets the
dashboard light up "where is the gap" on the same hexes as the satellite layer.

Reads a GeoJSONSeq stream on stdin (osmium export of the tertiary+ extract, whose
tags survive — unlike data/roads.parquet which dropped them). Reuses the H3
binning convention from 04_build_cells.py (segmentize ~22 m, h3.latlng_to_cell
res 10) and geodesic length from the baseline scripts (pyproj Geod WGS84).

Usage:
    osmium export osm-enrichment/baseline/vn-major.osm.pbf -f geojsonseq \\
        --geometry-types=linestring \\
      | coverage/.venv/bin/python coverage/prep/05_road_coverage.py

Output: data/road_coverage_cells.parquet  [h3_id, road_km, maxspeed_km,
        name_km, lanes_km, top_class]  (one row per cell that has a tertiary+ road)
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import h3
import pandas as pd
from pyproj import Geod
from shapely.geometry import shape

DATA = Path(__file__).resolve().parents[1] / "data"
RES = 10
GEOD = Geod(ellps="WGS84")
DENSIFY_DEG = 0.0002  # ~22 m, < res-10 edge — same as 04_build_cells._line_cells

# class rank for "what is the strongest road in this cell"; _link folds to parent
RANK = {"tertiary": 1, "secondary": 2, "primary": 3, "trunk": 4, "motorway": 5}


def has_maxspeed(props):
    return any(k == "maxspeed" or k.startswith("maxspeed:") for k in props)


def base_class(hw):
    return hw[:-5] if hw.endswith("_link") else hw


def seg_lengths(lons, lats):
    """Geodesic length (m) of each consecutive vertex pair, vectorised."""
    _, _, dist = GEOD.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])
    return dist


def main() -> int:
    # per cell: [road_m, maxspeed_m, name_m, lanes_m]
    acc = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    top = {}  # cell -> best base class
    total_m = 0.0

    for line in sys.stdin:
        line = line.strip("\x1e \t\r\n")
        if not line or line[0] != "{":
            continue
        feat = json.loads(line)
        props = feat.get("properties") or {}
        hw = props.get("highway")
        if not hw or base_class(hw) not in RANK:
            continue
        cls = base_class(hw)
        has_ms = has_maxspeed(props)
        has_nm = bool(props.get("name"))
        has_ln = "lanes" in props
        geom = feat.get("geometry") or {}
        try:
            g = shape(geom)
        except Exception:
            continue
        parts = g.geoms if g.geom_type == "MultiLineString" else [g]
        for ls in parts:
            if ls.is_empty or len(ls.coords) < 2:
                continue
            dense = ls.segmentize(DENSIFY_DEG)
            xs = [c[0] for c in dense.coords]
            ys = [c[1] for c in dense.coords]
            if len(xs) < 2:
                continue
            dists = seg_lengths(xs, ys)
            for i, d in enumerate(dists):
                mlat = (ys[i] + ys[i + 1]) / 2
                mlng = (xs[i] + xs[i + 1]) / 2
                cell = h3.latlng_to_cell(mlat, mlng, RES)
                a = acc[cell]
                a[0] += d
                if has_ms:
                    a[1] += d
                if has_nm:
                    a[2] += d
                if has_ln:
                    a[3] += d
                total_m += d
                if cell not in top or RANK[cls] > RANK[top[cell]]:
                    top[cell] = cls

    out = pd.DataFrame(
        [(c, v[0] / 1e3, v[1] / 1e3, v[2] / 1e3, v[3] / 1e3, top[c])
         for c, v in acc.items()],
        columns=["h3_id", "road_km", "maxspeed_km", "name_km", "lanes_km", "top_class"],
    )

    # Make the sidecar self-standing: most tertiary/secondary road cells are NOT
    # in cells.parquet (which only has urban + strategic-road + island cells), so
    # the dashboard must outer-merge. Carry the geometry + admin those new rows need.
    latlng = [h3.cell_to_latlng(c) for c in out["h3_id"]]
    out["lat"] = [p[0] for p in latlng]
    out["lng"] = [p[1] for p in latlng]
    out["cell_area_m2"] = [h3.cell_area(c, "m^2") for c in out["h3_id"]]
    out["res9_id"] = [h3.cell_to_parent(c, 9) for c in out["h3_id"]]

    admin = gpd.read_parquet(DATA / "admin_wards.parquet")
    pts = gpd.GeoDataFrame(out[["h3_id"]],
                           geometry=gpd.points_from_xy(out["lng"], out["lat"]),
                           crs=4326)
    j = (gpd.sjoin(pts, admin[["province", "ward", "geometry"]], how="left", predicate="within")
         .drop_duplicates("h3_id"))
    out = out.merge(j[["h3_id", "province", "ward"]], on="h3_id", how="left")

    out.to_parquet(DATA / "road_coverage_cells.parquet", index=False)
    print(f"wrote road_coverage_cells.parquet: {len(out):,} cells, "
          f"{out['province'].notna().mean()*100:.1f}% with province")
    print(f"  Σ road_km     = {out['road_km'].sum():,.0f}  (baseline tertiary+ ≈ 133,771)")
    print(f"  Σ maxspeed_km = {out['maxspeed_km'].sum():,.0f}  (baseline ≈ 17,273)")
    print(f"  Σ name_km     = {out['name_km'].sum():,.0f}")
    print(f"  Σ lanes_km    = {out['lanes_km'].sum():,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
