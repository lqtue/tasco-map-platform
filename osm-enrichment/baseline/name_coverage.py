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
from pyproj import Geod

GEOD = Geod(ellps="WGS84")
# Display classes from argv[1] (comma-sep) else tertiary+. _link variants of the
# classic hierarchy fold into their parent. argv[2] = output json filename.
DEFAULT = "motorway,trunk,primary,secondary,tertiary"
MAIN = [c.strip() for c in (sys.argv[1] if len(sys.argv) > 1 else DEFAULT).split(",")]
OUT = sys.argv[2] if len(sys.argv) > 2 else "name_coverage_result.json"
_LINKABLE = {"motorway", "trunk", "primary", "secondary", "tertiary"}
TRACKED = set(MAIN + [c + "_link" for c in MAIN if c in _LINKABLE])


def line_len_m(coords):
    if len(coords) < 2:
        return 0.0
    return GEOD.line_length([c[0] for c in coords], [c[1] for c in coords])


def feature_len_m(geom):
    t = geom.get("type")
    c = geom.get("coordinates") or []
    if t == "LineString":
        return line_len_m(c)
    if t == "MultiLineString":
        return sum(line_len_m(p) for p in c)
    return 0.0


def has_any_name(props):
    return any(k == "name" or k.startswith("name:") for k in props)


# base class (links folded into parent) -> [total_m, named_m, anyname_m]
stats = defaultdict(lambda: [0.0, 0.0, 0.0])

for line in sys.stdin:
    line = line.strip("\x1e \t\r\n")
    if not line or line[0] != "{":
        continue
    feat = json.loads(line)
    props = feat.get("properties") or {}
    hw = props.get("highway")
    if hw not in TRACKED:
        continue
    base = hw[:-5] if hw.endswith("_link") else hw
    m = feature_len_m(feat.get("geometry") or {})
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
