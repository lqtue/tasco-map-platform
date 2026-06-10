"""Step 3 — OSM strategic highways (built vs under-construction).

osmium-filters the latest VN PBF to motorway/trunk/primary (+_link) plus
highway=construction, exports linestrings, then classifies each way:
  status = "built"    -> operational tag  highway in TARGET
  status = "building" -> highway=construction AND construction in TARGET
Writes data/roads.parquet [class, status, geometry(LineString)] in EPSG:4326.
"""
import json
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import shape
from shapely.ops import polygonize, unary_union

ROOT = Path(__file__).resolve().parents[2]
PBF = ROOT / "osm-enrichment" / "baseline" / "vietnam-latest.osm.pbf"
DATA = Path(__file__).resolve().parents[1] / "data"
ROADS_PBF = DATA / "roads.osm.pbf"
ROADS_SEQ = DATA / "roads.geojsonseq"
OUT = DATA / "roads.parquet"
COAST_PBF = DATA / "coast.osm.pbf"
COAST_SEQ = DATA / "coast.geojsonseq"
COAST_OUT = DATA / "island_land.parquet"
ADMIN = DATA / "admin_wards.parquet"

TARGET = {"motorway", "trunk", "primary",
          "motorway_link", "trunk_link", "primary_link"}


def road_class(value: str) -> str:
    return value.removesuffix("_link")


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    run(["osmium", "tags-filter", str(PBF),
         f"w/highway={','.join(sorted(TARGET))}",
         "w/highway=construction",
         "-o", str(ROADS_PBF), "--overwrite"])
    run(["osmium", "export", str(ROADS_PBF),
         "-f", "geojsonseq", "--geometry-types=linestring",
         "-o", str(ROADS_SEQ), "--overwrite"])

    rows = []
    with open(ROADS_SEQ, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip().lstrip("\x1e")  # geojsonseq may RS-prefix
            if not line:
                continue
            feat = json.loads(line)
            props = feat.get("properties", {})
            hw = props.get("highway")
            if hw in TARGET:
                status, cls = "built", road_class(hw)
            elif hw == "construction":
                con = props.get("construction", "")
                if con not in TARGET:
                    continue
                status, cls = "building", road_class(con)
            else:
                continue
            rows.append({"class": cls, "status": status,
                         "geometry": shape(feat["geometry"])})

    g = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
    g.to_parquet(OUT)
    print(f"\nwrote {OUT}  ({len(g)} ways)")
    print(g.groupby(["status", "class"]).size().to_string())

    island_land()


def island_land() -> None:
    """Extract OSM coastline, polygonize into land polygons, keep those that
    fall inside the đặc khu island zones -> data/island_land.parquet."""
    run(["osmium", "tags-filter", str(PBF), "w/natural=coastline",
         "-o", str(COAST_PBF), "--overwrite"])
    run(["osmium", "export", str(COAST_PBF),
         "-f", "geojsonseq", "--geometry-types=linestring",
         "-o", str(COAST_SEQ), "--overwrite"])

    islands = gpd.read_parquet(ADMIN)
    islands = islands[islands["is_island"]]
    zone = unary_union(islands.geometry.values)  # đặc khu envelope (incl. sea)

    lines = []
    with open(COAST_SEQ, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip().lstrip("\x1e")
            if not line:
                continue
            geom = shape(json.loads(line)["geometry"])
            if geom.intersects(zone):           # only coast near the island zones
                lines.append(geom)

    polys = [p for p in polygonize(unary_union(lines)) if p.intersects(zone)]
    land = gpd.GeoDataFrame(geometry=polys, crs=4326)
    land = land[~land.intersection(zone).is_empty]
    land.to_parquet(COAST_OUT)
    print(f"wrote {COAST_OUT}  ({len(land)} island-land polygons, "
          f"{land.to_crs(3857).area.sum()/1e6:,.1f} km² raw)")


if __name__ == "__main__":
    sys.exit(main())
