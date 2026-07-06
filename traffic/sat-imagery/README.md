# Satellite imagery — coverage selection & procurement (partner demo)

Server-less static page for showing international partners how we **select** which
areas to buy satellite imagery for, and **track** procurement against that plan.

- `index.html` — the demo (MapLibre + plain JS, no build step). **Priority selector:**
  every hex is pre-scored (`priority = 0.6·density_percentile + 0.3·road_class +
  0.1·key_area`) and binned into 5 priority tiers (P1 densest cores → P5 rest of
  envelope); the panel lists each tier + its km² (and cumulative), and picking a tier
  images all higher tiers. Hero km², map colouring, **selection metrics** (avg built-up
  %, road-class mix), and **per-tier pricing** (`TIER_PRICE` USD/km²) update live.
- **Dual AOI export** (satellites image strips/scenes, not hexes): the ZIP bundles a
  pricing **summary**, the hex **archive mask** (`buildGeoJSON`, for coverage lookup),
  and **tasking footprints** (`taskingFeatures` — a bounding-box strip per contiguous
  cluster, padded to `MIN_FOOT_KM`, with `target_km²` vs billable `footprint_km²` and
  an `overhead_pct`). "Preview tasking footprints" overlays them on the map.
- `data.js` — baked H3 res-7 bundle (`window.DATA`); the only data the page needs.
  `sample_order.js` bakes the priority fields: `htier` (per-hex tier 1..5, 0=outside
  envelope), `tier_km2` (imaging km² per tier), plus `sample_order`/`sample_pri` for
  the free-sample optimizer. Tier bands + candidate envelope are tunable at its top.
- **Free-sample optimizer** — a partner enters the free km² they can offer; the page
  fills that budget by descending **per-hex priority** (`window.DATA.sample_order`,
  baked by `sample_order.js`: `priority = 0.6·density_percentile + 0.3·road_class +
  0.1·key_area`; `sample_pri` holds the scores), then dissolves the picked cells into
  scene-ready polygons (H3 cells merged, enclosed gaps filled — **not** hex tiles) and
  exports a ZIP. All geometry (spherical area, edge-cancellation dissolve,
  Douglas-Peucker smooth) is plain JS — no libraries (CSP forbids externals). Min
  budget 50 km². Weights/key-rule are tunable at the top of `sample_order.js`.

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
