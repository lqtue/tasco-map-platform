# Satellite imagery — coverage selection & procurement (partner demo)

Server-less static page for showing international partners how we **select** which
areas to buy satellite imagery for, and **track** procurement against that plan.

- `index.html` — the demo (MapLibre + plain JS, no build step). Toggle coverage
  layers (Urban / Roads), set urban-density threshold, road-class cutoff, and
  geographic scope; the map + selected km² + per-province tracking update live.
- `data.js` — baked H3 res-7 bundle (`window.DATA`); the only data the page needs.
- **Free-sample optimizer** — a partner enters the free km² they can offer; the page
  reveals cells from a pre-baked density-ranked, variety-seeded, contiguous growth
  order (`window.DATA.sample_order`), dissolves them into scene-ready polygons (H3
  cells merged, enclosed gaps filled — **not** hex tiles), and exports a ZIP. All
  geometry (spherical area, edge-cancellation dissolve, Douglas-Peucker smooth) is
  plain JS — no libraries (CSP forbids externals). Min budget 50 km².

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
