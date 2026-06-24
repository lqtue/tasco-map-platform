# maxspeed/

The **speed-limit (maxspeed) enrichment project** — self-contained so it can be managed on its own.
This is the live workstream (see the scope pivot in `../../CLAUDE.md` / Phụng meeting 2026-06-15).

```
maxspeed/
├── baseline/     ← reproducible OSM coverage stats (geodesic WGS84 km per highway class)
│   ├── run.sh                       download VN PBF → osmium filter → tally
│   ├── maxspeed_coverage.py + _result.json
│   ├── name_coverage.py / province_name_coverage.py + *_result.json
│   ├── morphology_coverage.py + _result.json   (law-default speed derivable today)
│   └── name_maxspeed_crosstab.py / _byroad.py  + *_result.json
├── dashboard/
│   └── app_maxspeed.py   ← single-problem Streamlit tracking dashboard (res-8 H3 gap map)
└── plans/
    └── maxspeed-name-edit-plan.md   ← operator deployment + budget (SUPERSEDED, see banner)
```

## Run

```bash
# Baseline: % of VN tertiary+ road km carrying a maxspeed tag (current: 12.9%)
bash traffic/maxspeed/baseline/run.sh

# Re-tally only (vn-major.osm.pbf already present)
osmium export traffic/maxspeed/baseline/vn-major.osm.pbf -f geojsonseq --geometry-types=linestring \
  | python3 traffic/maxspeed/baseline/maxspeed_coverage.py

# Dashboard (reads admin-poi/coverage/data/*.parquet for the H3 map)
admin-poi/coverage/.venv/bin/streamlit run traffic/maxspeed/dashboard/app_maxspeed.py
```

## Cross-project dependencies (intentional)

- **`admin-poi/coverage/data/`** parquets feed the dashboard's H3 map: `cells.parquet`,
  `road_coverage_cells.parquet` (per-cell maxspeed/name km, from `admin-poi/coverage/prep/05`), and the
  optional `mapillary_sign_points.parquet` (street-view signs, from `admin-poi/coverage/prep/06`). Those
  sidecars stay in `coverage/` by design.
- **Progress tracker** `../../dashboards/data/progress.json` is **shared** with the multi-product
  `../../dashboards/app.py` (single source of truth).
- **Legal reference** lives at `../../wiki/` (Thông tư 38/2024 → tag → speed matrix), the stated
  input for the maxspeed decision tree.

## Scope (per 2026-06-15)

Live worklist moved from H3 cells → **named national roads** (quốc lộ / cao tốc, motorway/trunk/
primary ≈ 28,000 km; tertiary + tỉnh lộ dropped). Tags: maxspeed + no-overtaking + residential-area
signs. Every edit needs verifiable street-view evidence in the changeset. The cell dashboard here
still runs but is no longer the worklist; a ranked road-list view is the next build.
