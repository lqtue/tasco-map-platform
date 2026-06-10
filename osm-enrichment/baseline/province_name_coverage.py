#!/usr/bin/env python3
"""No-name road km per province (tertiary+), via spatial join to admin polygons.

Reads GeoJSONSeq on stdin (osmium export), assigns each road to a province by its
geodesic midpoint, tallies total / named / no-name km. Admin source:
coverage/data/admin_wards.parquet (province column, EPSG:4326).

Usage:
    osmium export vn-major.osm.pbf -f geojsonseq --geometry-types=linestring \\
        | python3 province_name_coverage.py
"""
import json
import sys
import geopandas as gpd
from shapely.geometry import shape
from pyproj import Geod

GEOD = Geod(ellps="WGS84")
MAIN = {"motorway", "trunk", "primary", "secondary", "tertiary"}
ADMIN = "../../coverage/data/admin_wards.parquet"


def tracked(hw):
    if not hw:
        return False
    base = hw[:-5] if hw.endswith("_link") else hw
    return base in MAIN


def glen(coords):
    if len(coords) < 2:
        return 0.0
    return GEOD.line_length([c[0] for c in coords], [c[1] for c in coords])


pts, lens, named = [], [], []
for line in sys.stdin:
    line = line.strip("\x1e \t\r\n")
    if not line or line[0] != "{":
        continue
    f = json.loads(line)
    p = f.get("properties") or {}
    if not tracked(p.get("highway")):
        continue
    geom = f.get("geometry") or {}
    t, c = geom.get("type"), geom.get("coordinates") or []
    if t == "LineString":
        L = glen(c)
    elif t == "MultiLineString":
        L = sum(glen(x) for x in c)
    else:
        continue
    try:
        g = shape(geom)
        mp = g.interpolate(0.5, normalized=True)
    except Exception:
        continue
    pts.append(mp)
    lens.append(L)
    named.append(1 if p.get("name") else 0)

print(f"  roads parsed: {len(pts):,}", file=sys.stderr)
roads = gpd.GeoDataFrame({"len_m": lens, "named": named}, geometry=pts, crs="EPSG:4326")
roads["named_m"] = roads["len_m"] * roads["named"]

adm = gpd.read_parquet(ADMIN)
prov = adm.dissolve(by="province")[["geometry"]].reset_index()
print(f"  provinces: {len(prov)}", file=sys.stderr)

j = gpd.sjoin(roads, prov, how="left", predicate="within")
agg = (j.groupby("province")
         .agg(total_m=("len_m", "sum"), named_m=("named_m", "sum"))
         .reset_index())
agg["no_name_km"] = (agg["total_m"] - agg["named_m"]) / 1000
agg["total_km"] = agg["total_m"] / 1000
agg["named_km"] = agg["named_m"] / 1000
agg["pct_named"] = 100 * agg["named_m"] / agg["total_m"]
agg = agg.sort_values("no_name_km", ascending=False)

unknown_km = roads["len_m"].sum() / 1000 - agg["total_km"].sum()
print(f"\n{'province':<26}{'total_km':>10}{'no_name_km':>12}{'%named':>9}")
for _, r in agg.iterrows():
    print(f"{r['province']:<26}{r['total_km']:>10,.0f}{r['no_name_km']:>12,.0f}{r['pct_named']:>8.1f}%")
print("-" * 57)
print(f"{'TOTAL (assigned)':<26}{agg['total_km'].sum():>10,.0f}{agg['no_name_km'].sum():>12,.0f}"
      f"{100*agg['named_km'].sum()/agg['total_km'].sum():>8.1f}%")
if unknown_km > 1:
    print(f"{'(midpoint outside VN polys)':<26}{unknown_km:>10,.0f}")

agg[["province", "total_km", "named_km", "no_name_km", "pct_named"]].round(1) \
   .to_json("name_coverage_by_province.json", orient="records", force_ascii=False, indent=2)
