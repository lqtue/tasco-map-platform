"""Step 2 — Google Open Buildings v3 -> per-province building centroids (via GEE).

For each of the 34 provinces, clip Open Buildings (confidence >= 0.65) to the
province polygon and export building {lon, lat, area} centroids to Google Drive
as CSV. H3 assignment happens locally in Step 4 (GEE has no native H3).

Usage:
  EE_PROJECT=<id> python prep/02_gee_buildings.py            # launch all 34 tasks
  EE_PROJECT=<id> python prep/02_gee_buildings.py --only "thành phố Đà Nẵng"
  EE_PROJECT=<id> python prep/02_gee_buildings.py --monitor  # poll task status

After tasks finish, download the Drive folder `OB_VN_BUILDINGS` into
data/buildings/  (one or more CSV shards per province).
"""
import argparse
import os
import sys
import time
from pathlib import Path

import ee
import geopandas as gpd

ADMIN = Path(__file__).resolve().parents[1] / "data" / "admin_wards.parquet"
DRIVE_FOLDER = "OB_VN_BUILDINGS"
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
          .filterBounds(region))

    def to_point(feat):
        c = feat.geometry().centroid(1).coordinates()
        return ee.Feature(None, {"lon": c.get(0), "lat": c.get(1),
                                 "area": feat.get("area_in_meters")})

    out = fc.map(to_point)
    return ee.batch.Export.table.toDrive(
        collection=out,
        description=f"ob_{slug(name)}",
        folder=DRIVE_FOLDER,
        fileNamePrefix=f"ob_{slug(name)}",
        fileFormat="CSV",
        selectors=["lon", "lat", "area"],
    )


def monitor() -> None:
    while True:
        tasks = [t for t in ee.batch.Task.list()
                 if t.config.get("description", "").startswith("ob_")]
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
    ap.add_argument("--only", help="run a single province by exact name")
    ap.add_argument("--monitor", action="store_true")
    args = ap.parse_args()
    if not args.project:
        sys.exit("ERROR: set EE_PROJECT=<cloud-project-id> or pass --project")

    ee.Initialize(project=args.project)
    if args.monitor:
        monitor(); return 0

    geoms = province_geoms()
    if args.only:
        geoms = {args.only: geoms[args.only]}
    for name, gj in geoms.items():
        t = build_task(name, gj)
        t.start()
        print("started:", t.status()["description"], t.id)
    print(f"\n{len(geoms)} task(s) launched -> Drive folder '{DRIVE_FOLDER}'.")
    print("Poll with --monitor; then download CSVs into data/buildings/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
