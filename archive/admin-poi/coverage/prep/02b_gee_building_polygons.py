"""Step 2b — Google Open Buildings v3 -> per-province building POLYGONS (via GEE).

Unlike 02_gee_buildings.py (which exports centroids for H3 counting), this keeps
the full building footprint geometry + area_in_meters + confidence. Purpose:
spatial dedup of crawled POI data (point-in-polygon: POIs landing in the same
building footprint are duplicate candidates).

Output is GeoJSON (polygon geometry preserved) to Drive folder OB_VN_POLYGONS.
GeoJSON is verbose but the cleanest GEE polygon format; backend converts to
GeoParquet as needed.

Usage:
  EE_PROJECT=<id> python prep/02b_gee_building_polygons.py \
      --only "thành phố Hồ Chí Minh,Thủ đô Hà Nội"   # launch a subset
  EE_PROJECT=<id> python prep/02b_gee_building_polygons.py            # all 34
  EE_PROJECT=<id> python prep/02b_gee_building_polygons.py --monitor  # poll

After tasks finish, download the Drive folder OB_VN_POLYGONS into
data/buildings_polygons/.
"""
import argparse
import os
import sys
import time
from pathlib import Path

import ee
import geopandas as gpd

ADMIN = Path(__file__).resolve().parents[1] / "data" / "admin_wards.parquet"
DRIVE_FOLDER = "OB_VN_POLYGONS"
OB = "GOOGLE/Research/open-buildings/v3/polygons"
MIN_CONFIDENCE = 0.65
SIMPLIFY_M = 100  # province-polygon simplification for the clip region


def province_geoms() -> dict[str, dict]:
    g = gpd.read_parquet(ADMIN)
    prov = g.dissolve(by="province")["geometry"].simplify(SIMPLIFY_M / 111_000)
    return {name: geom.__geo_interface__ for name, geom in prov.items()}


def slug(name: str) -> str:
    import unicodedata
    name = name.replace("đ", "d").replace("Đ", "D")  # NFKD won't ASCII-fold these
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "_".join(n.split())


def build_task(name: str, geojson: dict) -> ee.batch.Task:
    region = ee.Geometry(geojson)
    fc = (ee.FeatureCollection(OB)
          .filter(ee.Filter.gte("confidence", MIN_CONFIDENCE))
          .filterBounds(region)
          .select(["area_in_meters", "confidence"]))  # keep geometry + these props
    return ee.batch.Export.table.toDrive(
        collection=fc,
        description=f"obpoly_{slug(name)}",
        folder=DRIVE_FOLDER,
        fileNamePrefix=f"obpoly_{slug(name)}",
        fileFormat="GeoJSON",
    )


def monitor() -> None:
    while True:
        tasks = [t for t in ee.batch.Task.list()
                 if t.config.get("description", "").startswith("obpoly_")]
        states = {}
        for t in tasks[:40]:
            s = t.status()["state"]
            states[s] = states.get(s, 0) + 1
        print(time.strftime("%H:%M:%S"), states)
        if not states.get("RUNNING") and not states.get("READY"):
            print("all done"); return
        time.sleep(60)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.environ.get("EE_PROJECT"))
    ap.add_argument("--only", help="comma-separated province names (exact)")
    ap.add_argument("--monitor", action="store_true")
    args = ap.parse_args()
    if not args.project:
        sys.exit("ERROR: set EE_PROJECT=<cloud-project-id> or pass --project")

    ee.Initialize(project=args.project)
    if args.monitor:
        monitor(); return 0

    geoms = province_geoms()
    if args.only:
        want = [s.strip() for s in args.only.split(",")]
        missing = [w for w in want if w not in geoms]
        if missing:
            sys.exit(f"ERROR: unknown province(s): {missing}")
        geoms = {w: geoms[w] for w in want}
    for name, gj in geoms.items():
        t = build_task(name, gj)
        t.start()
        print("started:", t.status()["description"], t.id)
    print(f"\n{len(geoms)} task(s) launched -> Drive folder '{DRIVE_FOLDER}'.")
    print("Poll with --monitor; then download GeoJSON into data/buildings_polygons/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
