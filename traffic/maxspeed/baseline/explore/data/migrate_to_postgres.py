#!/usr/bin/env python3
"""search.sqlite -> CSVs for \\copy into PostGIS (tasco_geo db).

No python postgres driver needed: dumps CSV, psql \\copy does the bulk load. CSVs land at
config.ROOT so load.sql (run from the explore/ dir) finds them via relative \\copy paths.

Run (from the explore/ dir):
  .venv/bin/python3 data/migrate_to_postgres.py && psql -d tasco_geo -f data/load.sql
"""
import csv
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import config

SRC = sqlite3.connect(config.SQLITE)
OUT = config.ROOT


def way_wkt(geom_json):
    coords = json.loads(geom_json)  # [[lat,lon], ...]
    pts = ",".join(f"{lon} {lat}" for lat, lon in coords)
    return f"LINESTRING({pts})"


with open(OUT / "way_stage.csv", "w", newline="") as f:
    w = csv.writer(f)
    for wid, version, tags, geom, node_ids in SRC.execute(
        "SELECT id, version, tags, geom, node_ids FROM way"
    ):
        w.writerow([wid, version, tags, way_wkt(geom), node_ids])

with open(OUT / "relation.csv", "w", newline="") as f:
    w = csv.writer(f)
    for rid, ref, name, tags in SRC.execute("SELECT id, ref, name, tags FROM relation"):
        w.writerow([rid, ref, name, tags])

with open(OUT / "rel_member.csv", "w", newline="") as f:
    w = csv.writer(f)
    for rid, wid in SRC.execute("SELECT rel_id, way_id FROM rel_member"):
        w.writerow([rid, wid])

print(f"wrote way_stage.csv, relation.csv, rel_member.csv to {OUT}")
