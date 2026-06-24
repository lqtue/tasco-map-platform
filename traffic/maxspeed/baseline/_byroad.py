import sys
from collections import defaultdict

from geo import MAIN_CLASSES, feature_len_m, iter_geojsonseq

MAIN = set(MAIN_CLASSES)

# key -> [total_m, maxspeed_m, {classes}, {names}, {maxspeed values}]
st = defaultdict(lambda: [0.0, 0.0, set(), set(), set()])
for p, geom in iter_geojsonseq(sys.stdin):
    hw = p.get("highway")
    if hw not in MAIN: continue
    ref = p.get("ref"); nm = p.get("name")
    key = ref or nm
    if not key: continue
    m = feature_len_m(geom)
    if m <= 0: continue
    s = st[key]; s[0] += m
    if "maxspeed" in p:
        s[1] += m; s[4].add(p["maxspeed"])
    s[2].add(hw)
    if nm: s[3].add(nm)

rows = []
for k, s in st.items():
    rows.append((k, s[0] / 1000, s[1] / 1000, 100 * s[1] / s[0] if s[0] else 0,
                 ",".join(sorted(s[2])), (sorted(s[3])[:1] or [""])[0],
                 ",".join(sorted(s[4]))))
rows.sort(key=lambda r: -r[1])

print("{:<12}{:>9}{:>9}{:>7}  {:<20}{:<28}{}".format(
    "ref/name", "km", "ms_km", "%ms", "class", "name", "ms_values"))
print("-" * 118)
for r in rows[:80]:
    print("{:<12}{:>9.1f}{:>9.1f}{:>6.1f}%  {:<20}{:<28}{}".format(*r))
