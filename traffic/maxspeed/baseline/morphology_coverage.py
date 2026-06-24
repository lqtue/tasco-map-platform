#!/usr/bin/env python3
"""Length-weighted morphology-tag coverage of Vietnam's tertiary+ network.

The Thông tư 38 speed decision keys on road morphology — lane count, one-way /
divided carriageway, built-up area — NOT on highway class. This tallies how many
geodesic km of tertiary+ already carry the morphology tags the law rule needs,
i.e. the slice where a law-default speed can be derived today vs the slice that
needs satellite/streetview observation first.

Reuses the geodesic (WGS84) method from maxspeed_coverage.py.

Usage:
    osmium export vn-major.osm.pbf -f geojsonseq --geometry-types=linestring \\
        | python3 morphology_coverage.py
"""
import json
import sys
from collections import defaultdict

from geo import MAIN_CLASSES, feature_len_m, iter_geojsonseq, km, pct

MAIN = MAIN_CLASSES
TRACKED = set(MAIN + [c + "_link" for c in MAIN])

# per class: total, lanes, oneway(any), oneway=yes, maxspeed, full-morph(lanes & oneway)
stats = defaultdict(lambda: [0.0] * 6)

for props, geom in iter_geojsonseq(sys.stdin):
    hw = props.get("highway")
    if hw not in TRACKED:
        continue
    m = feature_len_m(geom)
    if m <= 0:
        continue
    has_lanes = "lanes" in props
    has_oneway = "oneway" in props
    oneway_yes = props.get("oneway") == "yes"
    has_ms = "maxspeed" in props
    s = stats[hw]
    s[0] += m
    if has_lanes:
        s[1] += m
    if has_oneway:
        s[2] += m
    if oneway_yes:
        s[3] += m
    if has_ms:
        s[4] += m
    if has_lanes and has_oneway:
        s[5] += m


agg = [0.0] * 6
for c in MAIN:
    s = stats.get(c)
    if s:
        for i in range(6):
            agg[i] += s[i]

print("\n=== OSM morphology-tag coverage — Vietnam, tertiary+ (geodesic km) ===\n")
hdr = ("class", "total_km", "lanes_km", "%lanes", "oneway%", "1way=yes%", "lanes&oneway%")
print("{:<14}{:>11}{:>11}{:>9}{:>9}{:>11}{:>15}".format(*hdr))
print("-" * 80)
for c in MAIN:
    s = stats.get(c)
    if not s:
        continue
    print("{:<14}{:>11.1f}{:>11.1f}{:>8.1f}%{:>8.1f}%{:>10.1f}%{:>14.1f}%".format(
        c, km(s[0]), km(s[1]), pct(s[1], s[0]), pct(s[2], s[0]), pct(s[3], s[0]), pct(s[5], s[0])))
print("-" * 80)
print("{:<14}{:>11.1f}{:>11.1f}{:>8.1f}%{:>8.1f}%{:>10.1f}%{:>14.1f}%".format(
    "TERTIARY+", km(agg[0]), km(agg[1]), pct(agg[1], agg[0]), pct(agg[2], agg[0]),
    pct(agg[3], agg[0]), pct(agg[5], agg[0])))

print("\nHeadline (the law-default question):")
print(f"  Tertiary+ length            : {km(agg[0]):,.0f} km")
print(f"  Has lane count              : {km(agg[1]):,.0f} km  ({pct(agg[1], agg[0]):.1f}%)")
print(f"  Has oneway tag              : {km(agg[2]):,.0f} km  ({pct(agg[2], agg[0]):.1f}%)")
print(f"  Has BOTH lanes & oneway     : {km(agg[5]):,.0f} km  ({pct(agg[5], agg[0]):.1f}%)")
print(f"  -> needs sat/SV observation : {km(agg[0]-agg[5]):,.0f} km  ({100-pct(agg[5], agg[0]):.1f}%)")

out = {
    "unit": "km_geodesic_wgs84",
    "classes": {c: {
        "total_km": km(stats[c][0]), "lanes_km": km(stats[c][1]),
        "oneway_km": km(stats[c][2]), "oneway_yes_km": km(stats[c][3]),
        "maxspeed_km": km(stats[c][4]), "lanes_and_oneway_km": km(stats[c][5]),
    } for c in stats},
    "tertiary_plus": {
        "total_km": km(agg[0]), "lanes_km": km(agg[1]), "oneway_km": km(agg[2]),
        "oneway_yes_km": km(agg[3]), "lanes_and_oneway_km": km(agg[5]),
    },
}
with open("morphology_coverage_result.json", "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("\nWrote morphology_coverage_result.json")
