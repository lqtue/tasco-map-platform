# Satellite imagery — coverage selection & procurement (partner demo)

Server-less static page for showing international partners how we **select** which
areas to buy satellite imagery for, and **track** procurement against that plan.

- `index.html` — the demo (MapLibre + plain JS, no build step). Toggle coverage
  layers (Urban / Roads), set urban-density threshold, road-class cutoff, and
  geographic scope; the map + selected km² + per-province tracking update live.
- `data.js` — baked H3 res-7 bundle (`window.DATA`); the only data the page needs.

## Run locally
```
python3 -m http.server -d traffic/sat-imagery 8400   # then open http://localhost:8400/
```
(or just open `index.html` — `data.js` loads over `file://` too.)

## Refresh the data
`data.js` is regenerated from the coverage pipeline (parquets + baseline JSONs):
```
archive/admin-poi/coverage/.venv/bin/python archive/dashboards/export_static.py
```
That script writes straight into this folder. Bump the `?v=N` on the `data.js`
`<script>` tag in `index.html` when the schema changes, to bust browser caches.

Published at https://lqtue.github.io/tasco-map-platform/sat-imagery/
