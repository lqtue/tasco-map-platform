"""Per-route maxspeed *profile* + edit *freshness*, for the dashboard's inline sparkline.

`route_coverage.py` answers "how much of each route carries maxspeed". This sidecar adds
the two things the dashboard sparkline needs that the coverage JSON can't carry: the
maxspeed *value* along the route and *how recently each piece was last edited* (OSM
`timestamp`, which only the PBF has — Overpass-on-load for 410 routes would be too heavy).

For each route ref it walks the member ways in relation order, then bins them into a fixed
number of equal-count buckets so every route is a compact, same-shape little chart:

  bins[i] = [maxspeed_code, age_days]
    maxspeed_code : km/h int, 0 = no maxspeed tag, -1 = tag present but non-numeric
    age_days      : days since last edit (oldest segment in the bin — conservative for QA)

Plus a length-weighted median edit-age per route (the sortable "freshness" column).

Run:  admin-poi/coverage/.venv/bin/python traffic/maxspeed/baseline/route_freshness.py \\
        [vietnam-latest.osm.pbf]
Writes route_freshness.json next to the script (copy it into traffic/lanes/static/data/).
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import osmium

from geo import GEOD, MAIN_CLASSES, base_class, iter_road_routes, ms_code

MAIN = set(MAIN_CLASSES)
NBINS = 60  # bars per route sparkline


def main(pbf):
    # Pass 1: way_id -> (km, ms_code, timestamp). Member order, not geometry, drives the
    # sparkline x-axis, so we don't need node endpoints here.
    ways = {}
    newest = datetime(1970, 1, 1, tzinfo=timezone.utc)
    fp = osmium.FileProcessor(pbf).with_locations()
    for o in fp:
        if not o.is_way() or base_class(o.tags.get("highway")) not in MAIN:
            continue
        coords = [(n.lon, n.lat) for n in o.nodes if n.location.valid()]
        if len(coords) < 2:
            continue
        km = GEOD.line_length([c[0] for c in coords], [c[1] for c in coords]) / 1000
        ts = o.timestamp
        newest = max(newest, ts)
        ways[o.id] = (km, ms_code(o.tags.get("maxspeed")), ts)

    # Pass 2: route=road relations grouped by ref -> member way ids in encounter order
    order = defaultdict(list)
    seen = defaultdict(set)
    for ref, o in iter_road_routes(pbf):
        for m in o.members:
            if m.type == "w" and m.ref in ways and m.ref not in seen[ref]:
                seen[ref].add(m.ref)
                order[ref].append(m.ref)

    snapshot = newest.date().isoformat()
    routes = {}
    for ref, wids in order.items():
        segs = [ways[w] for w in wids]  # (km, ms, ts) in route order
        total = sum(s[0] for s in segs)
        if total <= 0:
            continue
        age = {w: (newest - ways[w][2]).days for w in wids}

        # equal-km bins; assign each segment to the bin of its midpoint
        binw = total / NBINS
        ms_by_bin = [defaultdict(float) for _ in range(NBINS)]  # bin -> {ms: km}
        age_by_bin = [0] * NBINS
        pos = 0.0
        for w, (km, ms, _ts) in zip(wids, segs):
            b = min(int((pos + km / 2) / binw), NBINS - 1)
            ms_by_bin[b][ms] += km
            age_by_bin[b] = max(age_by_bin[b], age[w])
            pos += km
        bins = []
        for b in range(NBINS):
            d = ms_by_bin[b]
            ms = max(d, key=d.get) if d else 0  # dominant maxspeed in the bin
            bins.append([ms, age_by_bin[b]])

        # length-weighted median edit age
        flat = sorted(((age[w], ways[w][0]) for w in wids))
        half, acc, med = total / 2, 0.0, flat[-1][0]
        for a, km in flat:
            acc += km
            if acc >= half:
                med = a
                break
        routes[ref] = {"bins": bins, "med_age": med}

    out = Path(__file__).with_name("route_freshness.json")
    out.write_text(json.dumps({"snapshot": snapshot, "routes": routes}, ensure_ascii=False))
    print(f"{len(routes)} routes · snapshot {snapshot} · wrote {out.name} "
          f"({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         str(Path(__file__).with_name("vietnam-latest.osm.pbf")))
