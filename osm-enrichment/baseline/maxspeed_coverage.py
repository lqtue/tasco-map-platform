#!/usr/bin/env python3
"""Length-weighted maxspeed coverage of Vietnam's tertiary+ road network from OSM.

Reads a GeoJSONSeq stream (one GeoJSON Feature per line, as produced by
`osmium export -f geojsonseq`) on stdin, computes geodesic length (WGS84) per
highway class, and reports how many km carry a maxspeed tag.

Usage:
    osmium export vn-major.osm.pbf -f geojsonseq --geometry-types=linestring \\
        | python3 maxspeed_coverage.py
"""
import json
import sys
from collections import defaultdict
from pyproj import Geod

GEOD = Geod(ellps="WGS84")

# "tertiary trở lên" — main hierarchy, highest → lowest importance.
MAIN = ["motorway", "trunk", "primary", "secondary", "tertiary"]
LINKS = [c + "_link" for c in MAIN]
TRACKED = set(MAIN + LINKS)


def line_len_m(coords):
    if len(coords) < 2:
        return 0.0
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return GEOD.line_length(lons, lats)


def feature_len_m(geom):
    t = geom.get("type")
    c = geom.get("coordinates") or []
    if t == "LineString":
        return line_len_m(c)
    if t == "MultiLineString":
        return sum(line_len_m(part) for part in c)
    return 0.0


# per class: [total_m, with_maxspeed_m, with_any_maxspeed_m, count, count_with_maxspeed]
stats = defaultdict(lambda: [0.0, 0.0, 0.0, 0, 0])


def has_any_maxspeed(props):
    return any(k == "maxspeed" or k.startswith("maxspeed:") for k in props)


for line in sys.stdin:
    line = line.strip()
    if not line or line[0] != "{":
        continue
    feat = json.loads(line)
    props = feat.get("properties") or {}
    hw = props.get("highway")
    if hw not in TRACKED:
        continue
    m = feature_len_m(feat.get("geometry") or {})
    if m <= 0:
        continue
    has_main = "maxspeed" in props
    has_any = has_any_maxspeed(props)
    s = stats[hw]
    s[0] += m
    if has_main:
        s[1] += m
    if has_any:
        s[2] += m
    s[3] += 1
    if has_main:
        s[4] += 1


def km(x):
    return x / 1000.0


def pct(a, b):
    return (100.0 * a / b) if b else 0.0


def row(label, s):
    return (label, km(s[0]), km(s[1]), pct(s[1], s[0]), km(s[2]), pct(s[2], s[0]), s[3], s[4])


print("\n=== OSM maxspeed coverage — Vietnam, tertiary+ (length-weighted) ===\n")
hdr = ("class", "total_km", "maxspeed_km", "%maxspeed", "anyMS_km", "%anyMS", "n_ways", "n_ms")
print("{:<16}{:>11}{:>13}{:>11}{:>11}{:>9}{:>9}{:>8}".format(*hdr))
print("-" * 88)


def line_out(r):
    print("{:<16}{:>11.1f}{:>13.1f}{:>10.1f}%{:>10.1f}{:>8.1f}%{:>9}{:>8}".format(*r))


agg_main = [0.0, 0.0, 0.0, 0, 0]
for c in MAIN:
    s = stats.get(c)
    if not s:
        continue
    line_out(row(c, s))
    for i in range(5):
        agg_main[i] += s[i]
print("-" * 88)
line_out(row("TERTIARY+ (sum)", agg_main))

agg_link = [0.0, 0.0, 0.0, 0, 0]
any_link = False
for c in LINKS:
    s = stats.get(c)
    if not s:
        continue
    any_link = True
    for i in range(5):
        agg_link[i] += s[i]
if any_link:
    print()
    line_out(row("(_link total)", agg_link))

print()
print("Headline:")
print(f"  Tertiary+ network length : {km(agg_main[0]):,.0f} km")
print(f"  With maxspeed tag        : {km(agg_main[1]):,.0f} km  ({pct(agg_main[1], agg_main[0]):.1f}%)")
print(f"  With any maxspeed* tag   : {km(agg_main[2]):,.0f} km  ({pct(agg_main[2], agg_main[0]):.1f}%)")
print(f"  Missing maxspeed         : {km(agg_main[0] - agg_main[1]):,.0f} km  ({100 - pct(agg_main[1], agg_main[0]):.1f}%)")

# machine-readable sidecar
out = {
    "unit": "km_geodesic_wgs84",
    "classes": {c: {
        "total_km": km(stats[c][0]), "maxspeed_km": km(stats[c][1]),
        "any_maxspeed_km": km(stats[c][2]), "pct_maxspeed": pct(stats[c][1], stats[c][0]),
        "n_ways": stats[c][3], "n_ways_maxspeed": stats[c][4],
    } for c in stats},
    "tertiary_plus": {
        "total_km": km(agg_main[0]), "maxspeed_km": km(agg_main[1]),
        "any_maxspeed_km": km(agg_main[2]), "pct_maxspeed": pct(agg_main[1], agg_main[0]),
    },
}
with open("maxspeed_coverage_result.json", "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("\nWrote maxspeed_coverage_result.json")
