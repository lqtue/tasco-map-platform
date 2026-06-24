#!/usr/bin/env python3
"""Length-weighted name coverage of Vietnam's tertiary+ road network from OSM.

Reads a GeoJSONSeq stream on stdin (as produced by `osmium export -f geojsonseq`),
computes geodesic length (WGS84) per highway class, and reports how many km carry
a `name` tag. Mirrors maxspeed_coverage.py.

Usage:
    osmium export vn-major.osm.pbf -f geojsonseq --geometry-types=linestring \\
        | python3 name_coverage.py
"""
import json
import sys
from collections import defaultdict

from geo import MAIN_CLASSES, base_class, feature_len_m, iter_geojsonseq

# _link variants of the classic hierarchy fold into their parent.
MAIN = MAIN_CLASSES
OUT = "name_coverage_result.json"
TRACKED = set(MAIN + [c + "_link" for c in MAIN])


def has_any_name(props):
    return any(k == "name" or k.startswith("name:") for k in props)


# base class (links folded into parent) -> [total_m, named_m, anyname_m]
stats = defaultdict(lambda: [0.0, 0.0, 0.0])

for props, geom in iter_geojsonseq(sys.stdin):
    hw = props.get("highway")
    if hw not in TRACKED:
        continue
    base = base_class(hw)
    m = feature_len_m(geom)
    stats[base][0] += m
    if props.get("name"):
        stats[base][1] += m
    if has_any_name(props):
        stats[base][2] += m

tot = [0.0, 0.0, 0.0]
print(f"{'class':<10}{'total_km':>12}{'named_km':>12}{'no_name_km':>12}{'%named':>9}")
for c in MAIN:
    t, n, a = stats[c]
    if t == 0:
        continue
    for i, v in enumerate((t, n, a)):
        tot[i] += v
    print(f"{c:<10}{t/1000:>12,.0f}{n/1000:>12,.0f}{(t-n)/1000:>12,.0f}{100*n/t:>8.1f}%")

t, n, a = tot
print("-" * 55)
print(f"{'TERT+':<10}{t/1000:>12,.0f}{n/1000:>12,.0f}{(t-n)/1000:>12,.0f}{100*n/t:>8.1f}%")
print(f"\n=> KHONG co name (base tag): {(t-n)/1000:,.0f} km / {t/1000:,.0f} km ({100*(t-n)/t:.1f}%)")
print(f"=> Co 'name' chuan: {n/1000:,.0f} km ({100*n/t:.1f}%); ke ca name:xx: {a/1000:,.0f} km ({100*a/t:.1f}%)")

result = {
    "scope": ",".join(MAIN) + " (+ _link folded into parent)",
    "total_km": round(t / 1000, 1),
    "named_km": round(n / 1000, 1),
    "no_name_km": round((t - n) / 1000, 1),
    "pct_named": round(100 * n / t, 1),
    "any_name_km": round(a / 1000, 1),
    "per_class": {c: {"total_km": round(stats[c][0] / 1000, 1),
                       "named_km": round(stats[c][1] / 1000, 1),
                       "no_name_km": round((stats[c][0] - stats[c][1]) / 1000, 1)}
                  for c in MAIN if stats[c][0] > 0},
}
with open(OUT, "w") as fh:
    json.dump(result, fh, ensure_ascii=False, indent=2)
