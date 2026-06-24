"""Per-route member-way geometry + current tags for the view/edit maxspeed tool.

route_coverage.py gives per-route *stats*; this gives the *geometry + current tags* so the
dashboard can draw a chosen route on a map (member ways colored by maxspeed presence) and
let an operator edit maxspeed — plus the supporting morphology (lanes, median/divider) that
makes a speed edit defensible under Thông tư 38. One row per (ref, member way):

  ref, way_id, base_class, has_maxspeed, oneway, km, path (JSON [[lon,lat], ...]),
  maxspeed, lanes, divided  (current tag values, "" / None if absent)

`divided` = a hint that opposing traffic is physically separated (dải phân cách giữa):
explicit oneway carriageway, motorway, or a divider/dual_carriageway/median tag present.

Run:  admin-poi/coverage/.venv/bin/python traffic/maxspeed/baseline/route_geom.py [pbf]
Writes route_geom.parquet next to the script (regenerable artifact — gitignored).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import osmium
import pandas as pd

from geo import GEOD, MAIN_CLASSES, base_class, is_oneway, iter_road_routes

MAIN = set(MAIN_CLASSES)


def is_divided(t, hw):
    """Opposing traffic physically separated (dải phân cách giữa) — defensible-speed signal."""
    return (is_oneway(t, hw)
            or t.get("dual_carriageway") == "yes"
            or t.get("divider") not in (None, "no")
            or "median" in t)


def main(pbf):
    # Pass 1: highway way geometry + current maxspeed/lanes/divided tags
    ways = {}
    fp = osmium.FileProcessor(pbf).with_locations()
    for o in fp:
        if not o.is_way():
            continue
        hw = o.tags.get("highway")
        if base_class(hw) not in MAIN:
            continue
        coords = [(round(n.lon, 6), round(n.lat, 6)) for n in o.nodes if n.location.valid()]
        if len(coords) < 2:
            continue
        km = GEOD.line_length([c[0] for c in coords], [c[1] for c in coords]) / 1000
        t = o.tags
        ways[o.id] = (coords, "maxspeed" in t, base_class(hw), is_oneway(t, hw), km,
                      t.get("maxspeed", ""), t.get("lanes", ""), is_divided(t, hw))

    # Pass 2: route=road relations -> member way ids per ref
    refways = defaultdict(set)
    for ref, o in iter_road_routes(pbf):
        for m in o.members:
            if m.type == "w" and m.ref in ways:
                refways[ref].add(m.ref)

    rows = []
    for ref, wids in refways.items():
        for wid in wids:
            coords, ms, cls, ow, km, mxs, lanes, divided = ways[wid]
            rows.append({"ref": ref, "way_id": wid, "base_class": cls, "has_maxspeed": ms,
                         "oneway": ow, "km": round(km, 3), "path": json.dumps(coords),
                         "maxspeed": mxs, "lanes": lanes, "divided": divided})

    df = pd.DataFrame(rows)
    out = Path(__file__).with_name("route_geom.parquet")
    df.to_parquet(out, index=False)
    print(f"{len(df):,} member-way rows · {df['ref'].nunique()} refs · "
          f"wrote {out.name} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         str(Path(__file__).with_name("vietnam-latest.osm.pbf")))
