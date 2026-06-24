"""Per-route maxspeed coverage via OSM route relations (the network-membership answer).

`_byroad.py` groups by the `ref` *tag* on individual ways — misses ways without ref
and can't tell if a road is actually one connected network. National highways in OSM
are instead grouped by **route relations** (`type=route, route=road, ref=QL.1`), which
collect every member way regardless of its local street `name` or province. This reads
those relations straight from the local pbf (pyosmium, no Overpass), and for each `ref`:

  - total geodesic km (WGS84) of member ways + km carrying a maxspeed tag (+ %),
  - highway classes spanned, number of member ways,
  - connected-component count (union-find on member-way endpoint nodes) → 1 = one
    continuous route; >1 = gaps / disjoint pieces (data issue or genuinely separate).

OSM models divided highways as two one-way carriageways, so summed member km ≈ carriageway
km, ~1.5-2x the official centerline length. So each route also reports a **centerline**
estimate = bidirectional_km + oneway_km/2 (halve the divided sections, keep two-way roads
whole). `oneway` = the tag (yes/-1/true/1) OR highway=motorway (oneway by OSM default).
Compare centerline_km — not member km — to official road-length statistics.

Run:  admin-poi/coverage/.venv/bin/python traffic/maxspeed/baseline/route_coverage.py \\
        traffic/maxspeed/baseline/vietnam-latest.osm.pbf
Writes route_coverage_result.json next to the script + prints a table.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import osmium

from geo import GEOD, MAIN_CLASSES, base_class, is_oneway, iter_road_routes

MAIN = set(MAIN_CLASSES)


class UF:
    """Union-find for counting connected components of member ways."""
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def main(pbf):
    # Pass 1: way_id -> (km, has_maxspeed, base_class, first_node, last_node)
    ways = {}
    fp = osmium.FileProcessor(pbf).with_locations()
    for o in fp:
        if not o.is_way():
            continue
        hw = o.tags.get("highway")
        if base_class(hw) not in MAIN:
            continue
        coords = [(n.lon, n.lat) for n in o.nodes if n.location.valid()]
        if len(coords) < 2:
            continue
        km = GEOD.line_length([c[0] for c in coords], [c[1] for c in coords]) / 1000
        ways[o.id] = (
            km,
            "maxspeed" in o.tags,
            base_class(hw),
            o.nodes[0].ref,
            o.nodes[-1].ref,
            is_oneway(o.tags, hw),
        )

    # Pass 2: route=road relations, grouped by ref
    # ref -> [km, ms_km, {classes}, {way_ids}, {names}, n_relations, {rel_ids}]
    agg = defaultdict(lambda: [0.0, 0.0, set(), set(), set(), 0, set()])
    for ref, o in iter_road_routes(pbf):
        a = agg[ref]
        a[5] += 1
        a[6].add(o.id)
        if o.tags.get("name"):
            a[4].add(o.tags["name"])
        for m in o.members:
            if m.type != "w" or m.ref not in ways:
                continue
            a[3].add(m.ref)

    # tally km from the deduped member way set + connectivity
    rows = []
    for ref, a in agg.items():
        uf = UF()
        km = ms = oneway_km = 0.0
        classes = set()
        for wid in a[3]:
            wkm, has_ms, cls, n0, n1, ow = ways[wid]
            km += wkm
            if has_ms:
                ms += wkm
            if ow:
                oneway_km += wkm
            classes.add(cls)
            uf.union(n0, n1)
        centerline = km - oneway_km / 2  # halve divided sections to estimate centerline
        comps = len({uf.find(ways[w][3]) for w in a[3]}) if a[3] else 0
        rows.append({
            "ref": ref,
            "km": round(km, 1),
            "centerline_km": round(centerline, 1),
            "maxspeed_km": round(ms, 1),
            "pct_maxspeed": round(100 * ms / km, 1) if km else 0.0,
            "classes": ",".join(sorted(classes)),
            "n_ways": len(a[3]),
            "n_relations": a[5],
            "components": comps,
            "name": sorted(a[4])[0] if a[4] else "",
            "rel_ids": sorted(a[6]),
        })
    rows.sort(key=lambda r: -r["km"])

    out = Path(__file__).with_name("route_coverage_result.json")
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2))

    print(f"{'ref':<14}{'km':>9}{'cline':>9}{'ms_km':>9}{'%ms':>6}  {'class':<20}"
          f"{'ways':>6}{'rels':>5}{'cc':>4}  name")
    print("-" * 104)
    for r in rows[:50]:
        print(f"{r['ref']:<14}{r['km']:>9.1f}{r['centerline_km']:>9.1f}{r['maxspeed_km']:>9.1f}"
              f"{r['pct_maxspeed']:>5.1f}%  {r['classes']:<20}{r['n_ways']:>6}{r['n_relations']:>5}"
              f"{r['components']:>4}  {r['name'][:28]}")
    tot = sum(r["km"] for r in rows)
    tot_c = sum(r["centerline_km"] for r in rows)
    print("-" * 104)
    print(f"{len(rows)} routes · {tot:,.0f} km member (carriageway) · "
          f"{tot_c:,.0f} km centerline · wrote {out.name}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         str(Path(__file__).with_name("vietnam-latest.osm.pbf")))
