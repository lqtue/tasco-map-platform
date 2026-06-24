"""National-road GeoJSON for the dashboard map (coloured by coverage / speed / freshness).

route_geom.py emits *all* member-way geometry as parquet for the per-route editor. This emits a
**compact, simplified GeoJSON of the national network only** (QL quốc lộ + CT cao tốc) for the
dashboard's overview map — one LineString per member way, simplified (Douglas-Peucker) and
coordinate-rounded so the whole country loads as one static file in the browser.

Per feature properties (the three colour modes the map offers):
  ref  : route ref            ms : maxspeed km/h, 0 = no tag, -1 = present non-numeric
  age  : days since last edit (OSM timestamp — only the PBF has it)

Run:  admin-poi/coverage/.venv/bin/python traffic/maxspeed/baseline/route_map.py [pbf]
Writes national_roads.geojson next to the script (copy into traffic/lanes/static/data/).
"""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import osmium
from shapely.geometry import LineString

from geo import MAIN_CLASSES, base_class, iter_road_routes, ms_code

MAIN = set(MAIN_CLASSES)
NATIONAL = re.compile(r"^(QL|CT)\b|^(QL|CT)\.", re.I)  # quốc lộ + cao tốc
SIMPLIFY = 0.0002  # ~22 m; nationwide overview, not survey accuracy


def main(pbf):
    # Pass 1: highway way geometry + maxspeed + timestamp
    ways = {}
    newest = datetime(1970, 1, 1, tzinfo=timezone.utc)
    fp = osmium.FileProcessor(pbf).with_locations()
    for o in fp:
        if not o.is_way() or base_class(o.tags.get("highway")) not in MAIN:
            continue
        coords = [(n.lon, n.lat) for n in o.nodes if n.location.valid()]
        if len(coords) < 2:
            continue
        newest = max(newest, o.timestamp)
        ways[o.id] = (coords, ms_code(o.tags.get("maxspeed")), o.timestamp)

    # Pass 2: route=road relations -> national member way ids per ref
    refways = defaultdict(set)
    for ref, o in iter_road_routes(pbf):
        if not NATIONAL.search(ref):
            continue
        for m in o.members:
            if m.type == "w" and m.ref in ways:
                refways[ref].add(m.ref)

    feats = []
    for ref, wids in refways.items():
        for wid in wids:
            coords, ms, ts = ways[wid]
            line = LineString(coords).simplify(SIMPLIFY, preserve_topology=False)
            pts = [[round(x, 5), round(y, 5)] for x, y in line.coords]
            if len(pts) < 2:
                continue
            feats.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": pts},
                "properties": {"ref": ref, "ms": ms, "age": (newest - ts).days},
            })

    out = Path(__file__).with_name("national_roads.geojson")
    out.write_text(json.dumps({
        "type": "FeatureCollection",
        "snapshot": newest.date().isoformat(),
        "features": feats,
    }, ensure_ascii=False))
    print(f"{len(feats):,} segments · {len(refways)} refs · "
          f"wrote {out.name} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         str(Path(__file__).with_name("vietnam-latest.osm.pbf")))
