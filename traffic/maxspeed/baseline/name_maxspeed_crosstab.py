#!/usr/bin/env python3
"""Joint cross-tab: road length by highway class × name presence × maxspeed presence.

Reads a GeoJSONSeq stream (`osmium export -f geojsonseq`) on stdin, computes
geodesic length (WGS84) per highway class, and reports km / % carrying a name
tag and a maxspeed tag, plus the 2×2 name×maxspeed breakdown.

Usage:
    osmium export vn-major.osm.pbf -f geojsonseq --geometry-types=linestring \\
        | python3 name_maxspeed_crosstab.py
"""
import json
import sys
from collections import defaultdict

from geo import MAIN_CLASSES, feature_len_m, iter_geojsonseq, km, pct

MAIN = MAIN_CLASSES
LINKS = [c + "_link" for c in MAIN]
TRACKED = set(MAIN + LINKS)


# per class: [total_m, name_m, maxspeed_m,
#             both_m, name_only_m, ms_only_m, neither_m, count]
stats = defaultdict(lambda: [0.0] * 7 + [0])


def has_maxspeed(props):
    return "maxspeed" in props


def has_name(props):
    return bool(props.get("name"))


for props, geom in iter_geojsonseq(sys.stdin):
    hw = props.get("highway")
    if hw not in TRACKED:
        continue
    m = feature_len_m(geom)
    if m <= 0:
        continue
    n = has_name(props)
    ms = has_maxspeed(props)
    s = stats[hw]
    s[0] += m
    if n:
        s[1] += m
    if ms:
        s[2] += m
    if n and ms:
        s[3] += m
    elif n and not ms:
        s[4] += m
    elif ms and not n:
        s[5] += m
    else:
        s[6] += m
    s[7] += 1


def row(label, s):
    return (label, km(s[0]),
            km(s[1]), pct(s[1], s[0]),
            km(s[2]), pct(s[2], s[0]),
            km(s[3]), km(s[4]), km(s[5]), km(s[6]), s[7])


print("\n=== OSM Vietnam tertiary+ : length by class × name × maxspeed (geodesic km) ===\n")
hdr = ("class", "total_km", "name_km", "%name", "ms_km", "%ms",
       "both_km", "nameOnly", "msOnly", "neither", "n_ways")
print("{:<16}{:>10}{:>10}{:>8}{:>10}{:>7}{:>9}{:>9}{:>8}{:>9}{:>8}".format(*hdr))
print("-" * 114)


def line_out(r):
    print("{:<16}{:>10.1f}{:>10.1f}{:>7.1f}%{:>10.1f}{:>6.1f}%{:>9.1f}{:>9.1f}{:>8.1f}{:>9.1f}{:>8}".format(*r))


agg = [0.0] * 7 + [0]
for c in MAIN:
    s = stats.get(c)
    if not s:
        continue
    line_out(row(c, s))
    for i in range(8):
        agg[i] += s[i]
print("-" * 114)
line_out(row("TERTIARY+ (sum)", agg))

agg_l = [0.0] * 7 + [0]
any_link = False
for c in LINKS:
    s = stats.get(c)
    if not s:
        continue
    any_link = True
    for i in range(8):
        agg_l[i] += s[i]
if any_link:
    print()
    line_out(row("(_link total)", agg_l))

print("\nHeadline (tertiary+ main):")
print(f"  Total network      : {km(agg[0]):,.0f} km")
print(f"  Has name           : {km(agg[1]):,.0f} km ({pct(agg[1], agg[0]):.1f}%)")
print(f"  Has maxspeed       : {km(agg[2]):,.0f} km ({pct(agg[2], agg[0]):.1f}%)")
print(f"  Both name+maxspeed : {km(agg[3]):,.0f} km ({pct(agg[3], agg[0]):.1f}%)")
print(f"  Name, no maxspeed  : {km(agg[4]):,.0f} km ({pct(agg[4], agg[0]):.1f}%)")
print(f"  Maxspeed, no name  : {km(agg[5]):,.0f} km ({pct(agg[5], agg[0]):.1f}%)")
print(f"  Neither            : {km(agg[6]):,.0f} km ({pct(agg[6], agg[0]):.1f}%)")

out = {
    "unit": "km_geodesic_wgs84",
    "classes": {c: {
        "total_km": km(s[0]), "name_km": km(s[1]), "maxspeed_km": km(s[2]),
        "pct_name": pct(s[1], s[0]), "pct_maxspeed": pct(s[2], s[0]),
        "both_km": km(s[3]), "name_only_km": km(s[4]),
        "ms_only_km": km(s[5]), "neither_km": km(s[6]), "n_ways": s[7],
    } for c, s in stats.items()},
    "tertiary_plus": {
        "total_km": km(agg[0]), "name_km": km(agg[1]), "maxspeed_km": km(agg[2]),
        "pct_name": pct(agg[1], agg[0]), "pct_maxspeed": pct(agg[2], agg[0]),
        "both_km": km(agg[3]), "name_only_km": km(agg[4]),
        "ms_only_km": km(agg[5]), "neither_km": km(agg[6]),
    },
}
with open("name_maxspeed_crosstab_result.json", "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("\nWrote name_maxspeed_crosstab_result.json")
