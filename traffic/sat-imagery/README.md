# Satellite imagery — coverage selection & procurement (partner demo)

Server-less static page for showing international partners how we **select** which
areas to buy satellite imagery for, and **track** procurement against that plan.

- `index.html` — the demo (MapLibre + plain JS, no build step). **Coverage-priority
  selector:** a **demo/trial** row with a slider (free-sample size — top-priority cells
  up to N km² via `D.sample_order`), then **4 rule-based tiers** — `1` densest urban,
  `2` dense urban + major road, `3` urban + primary, `4` rest of envelope — each with
  its km² (and cumulative); picking a tier images all higher tiers. **Tasking-footprint
  overlay is a toggle, default on.** No cost figures shown.
- `data.js` — baked H3 res-7 bundle (`window.DATA`); the only data the page needs.
  `sample_order.js` bakes `htier` (per-hex tier 1..4, 0=outside envelope), `tier_km2`
  (imaging km² per tier), and `sample_order` (priority order for the demo slider).
  Tier thresholds (`T1B/T2B/T3B`) + candidate envelope are tunable at its top.
- **Single bundle export** (satellites image strips, not hexes): one ZIP with a
  selection **summary** (per-province km²), the hex **archive mask** (`buildGeoJSON`,
  coverage lookup), and **tasking footprints** (`taskingFeatures` — bbox strip per
  contiguous cluster, padded to `MIN_FOOT_KM`, fully-contained boxes dropped,
  `deduped_footprint_km²` = union area so overlaps bill once, + `overhead_pct`).

## Run locally
```
python3 -m http.server -d traffic/sat-imagery 8400   # then open http://localhost:8400/
```
(or just open `index.html` — `data.js` loads over `file://` too.)

## Refresh the data
`data.js` is regenerated from the coverage pipeline (parquets + baseline JSONs):
```
archive/admin-poi/coverage/.venv/bin/python archive/dashboards/export_static.py
node traffic/sat-imagery/sample_order.js          # appends window.DATA.sample_order
```
`export_static.py` writes `data.js` straight into this folder; `sample_order.js`
then bakes the free-sample growth order into it (reads geometry + density from the
same file, no other inputs). Bump the `?v=N` on the `data.js` `<script>` tag in
`index.html` when the schema changes, to bust browser caches.

Published at https://lqtue.github.io/tasco-map-platform/sat-imagery/
