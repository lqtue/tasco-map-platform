# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository focus

> **Strategy & docs index:** [`docs/README.md`](docs/README.md) is the **orchestrator** — north star ([`docs/vision/`](docs/vision/): TASCO Mobility Platform + official OKR 2026.06), workstream↔owner↔status, leadership-present materials ([`docs/leadership/`](docs/leadership/)), meeting minutes, and the doc index. Read it for *why* the work below exists and how it ladders to the company goal.

This repo hosts **three initiatives**:
- **`osm-enrichment/` — current focus** (since 2026-06): the OSM Traffic Data Enrichment System. Start here.
- **`coverage/`** (built 2026-06): the Vietnam Imagery-Coverage Planner — an H3 + Open Buildings + OSM dashboard that decides *how much satellite imagery to buy and where*. Self-contained; see its own section below.
- The original **satellite tile platform** (`pipeline/`, `qgis-plugin/`, `config/`, `scripts/`) — **deprioritized**; feature-complete for the demo and documented in the lower sections.

## Project

TASCO Map Platform — satellite imagery tile server and tooling for MapOps editors. Initial AOI: greater Hanoi (MGRS tile T48QWJ, bbox `105.0,20.71,106.06,21.70`). Three independently deployable pieces:

1. **`pipeline/`** — Python CLIs: fetch HLS scenes from NASA, process into COGs, upload to R2/S3.
2. **`qgis-plugin/tasco_timeseries_viewer/`** — QGIS PyQt dock widget that loads dated imagery layers from the STAC catalog via XYZ tiles.
3. **`config/`** + **`scripts/setup-vps.sh`** — Docker Compose stack (TiTiler + Nginx) on Vultr VPS.

The three pieces share two contracts (not code imports):
- **R2 layout:** `{source}/{date}/composite.tif` (e.g. `sentinel2/2025-03/composite.tif`)
- **STAC catalog at `<server>/stac/catalog.json`:** custom shape `{"sources": {"<source>": [{"date": "YYYY-MM", "href": "<tile_url_template>", "cog_key": "..."}]}}`. The QGIS plugin also accepts standard STAC Catalog with child collection links as a fallback.

When changing either contract, update both `pipeline/upload.py::build_catalog` (producer) and `qgis-plugin/.../plugin.py::_parse_catalog` / `_parse_stac_standard` (consumer).

## OSM Traffic Data Enrichment (current focus)

`osm-enrichment/` automatically detects and adds three missing OSM attributes for Vietnam — **maxspeed**, **signalized intersections**, and **lane counts**. So far this is **planning + research + one analysis pipeline**; there is no application/model code for the three problems yet.

- `PROJECT_PLAN.md` — the proposal (Vietnamese). Architecture principle threaded throughout: **AI detects, rules/graph reason** (CNN for perception; legal rules + graph inference for conclusions; manual review for conflicts). Cite **RoadTagger (He et al., 2020)** for this claim, not the plan's unverifiable "Nilsson 2024".
- `research/README.md` — scite-verified annotated bibliography (22 papers) backing the three problems, also mirrored as a References section in `PROJECT_PLAN.md`. Keep the two in sync when adding sources.
- `baseline/` — reproducible OSM statistics pipeline (below).
- `STATUS_REPORT_*.md` — dated progress reports.

### Baseline pipeline (`osm-enrichment/baseline/`)

`run.sh` chains: download Geofabrik Vietnam PBF → `osmium tags-filter` to tertiary+ highways → `osmium export -f geojsonseq` → `maxspeed_coverage.py`, which tallies **geodesic (WGS84) km** per highway class and maxspeed presence via pyproj `Geod.line_length` (not projected/cartesian length — that would distort nationwide). Outputs a printed table + `maxspeed_coverage_result.json`.

Conventions baked into the analysis:
- **"tertiary+"** = `motorway, trunk, primary, secondary, tertiary` (+ `_link` variants, tallied separately). `unclassified` is excluded — in OSM it ranks *below* tertiary despite the name.
- "has maxspeed" = the *tag exists*, not that it is correct. Per-vehicle tags (`maxspeed:hgv`, `maxspeed:motorcycle`) count only toward the separate "any maxspeed*" column.
- Current result (extract 2026-06-06): tertiary+ ≈ 133,771 km, **12.9%** carry maxspeed.

The `.pbf` files (`vietnam-latest.osm.pbf` ~309 MB, `vn-major.osm.pbf`) are large regenerable artifacts — do **not** commit them (they are not yet in `.gitignore`; add them before any commit).

## Vietnam Imagery-Coverage Planner (`coverage/`)

Decides **how much satellite imagery to buy and where**. Tiles Vietnam with the Uber **H3** grid (res 10) **only around three targets** — urban/built-up, strategic highways (operational + under construction), islands — attaches per-cell evidence, and ships a **Streamlit + pydeck** dashboard where thresholds are *live filters* and total **km²** (and cost = km² × $/km²) update instantly. Nothing is baked in: the team tries criteria and reads the resulting buy-envelope.

**Core architecture — a 4-step prep chain produces ONE contract, `data/cells.parquet`, that the dashboard consumes.** Each `prep/0N_*.py` writes a parquet the next step reads; `dashboard/app.py` only ever loads `cells.parquet` (+ `cells_res9.parquet`). The pipeline is **sparse by design** — candidate cells are generated only around targets (~5M res-10 cells), never the whole country.

- `prep/01_admin.py` → `data/admin_wards.parquet` `[ma, province, ward, loai, is_island, geometry]`. Source: `~/Downloads/VietnamWardBoundary2025.geojson` (already EPSG:4326). **Islands = `loai == "đặc khu"`** (13 special zones); provinces = `tentinh` (34), wards = `tenhc` (3321). Asserts those counts.
- `prep/02_gee_buildings.py` → launches **34 per-province Earth Engine exports** of Open Buildings v3 centroids (`confidence ≥ 0.65`) as `{lon,lat,area}` CSV to Drive folder `OB_VN_BUILDINGS`. **Why centroids, not a raster, and why per-province:** a 10 m built-up raster of Vietnam is ~10⁹ px; sparse centroids are compact and let H3 assignment happen locally. **GEE has no native H3** — this is the whole reason assignment is deferred to step 4.
- `prep/03_osm_roads.py` → `data/roads.parquet` `[class, status, geometry]` via `osmium tags-filter` on `osm-enrichment/baseline/vietnam-latest.osm.pbf`. Also derives `data/island_land.parquet` by polygonizing OSM `natural=coastline` and intersecting with đặc khu zones.
- `prep/04_build_cells.py` → unions the three sources into `data/cells.parquet` (one row per `h3_id`) + a `cells_res9.parquet` rollup. **Urban assignment uses DuckDB's `h3` community extension** (`h3_latlng_to_cell_string(lat,lon,10)`) over the building CSVs — this produces **identical ids to python `h3`**, so DuckDB (fast, for millions of points) and python-h3 (roads/islands) interoperate. `_monitor.py` is a throwaway EE task-state poller.

**`cells.parquet` schema (the prep↔dashboard contract):** `h3_id, built_up_area_m2, building_count, road_built, road_built_class, road_construction, road_constr_class, is_island, is_island_land, cell_area_m2, built_up_ratio (clipped [0,1]), res9_id, lat, lng, province, ward`. The dashboard's selection rule = **union of any enabled criterion**, intersected with the province filter; category km² breakdowns intentionally overlap.

**Island maritime-inflation gotcha:** đặc khu admin polygons enclose large open sea (Trường Sa ≈ 4,360 km² of mostly water), so full-zone island area (~6,370 km²) massively overstates land. `is_island_land` (OSM-coastline-derived, ~867 km²) is the honest extent; the dashboard exposes both as a **"Island extent" radio**. When touching island logic, keep both flags.

**Conventions:** canonical Uber H3 v4 ids, **res 10** (~16,470 m²/cell), `res9_id` parent for zoom-out. Roads: `highway` ∈ {motorway, trunk, primary} (+`_link`); `built` = operational tag, `building` = `highway=construction` with matching `construction` tag. Urban threshold (`built_up_ratio`) is a **slider, never hard-coded** — default 10% ≈ "core built-up"; "any building" catches rural farm structures and is ~5× larger, so don't quote it as urban.

**Environment (matches repo-wide gotchas):** dedicated venv at `coverage/.venv` on **python3.13** (not 3.14 — PEP 668 + missing wheels). **`fiona` is broken** (GDAL dylib mismatch) → read GPKG/GeoJSON via geopandas/pyogrio only. Step 2 needs an **Earth Engine Cloud project** (`EE_PROJECT=<id>`); the project in use is `propane-avatar-430409-r2`.

**Retrieving the building CSVs from Drive (~3.4 GB, 34 files):** an **rclone `gdrive:` remote** (read-only OAuth) is configured — `rclone copy gdrive:OB_VN_BUILDINGS coverage/data/buildings --include "*.csv"`. The MCP Google Drive `download_file_content` tool is **not** usable here: it returns base64 into context and these files are 50–280 MB each. Do **not** use stored Earth Engine credentials to hit the Drive API for this (a safety classifier blocks credential enumeration). CSVs are transient — after step 4 aggregates them they can be deleted (they persist in Drive and locally enable re-aggregation at a different H3 resolution without re-download).

**Run it:**
```bash
PY=coverage/.venv/bin/python
$PY coverage/prep/01_admin.py
EE_PROJECT=<id> $PY coverage/prep/02_gee_buildings.py            # launch exports; --monitor to poll
rclone copy gdrive:OB_VN_BUILDINGS coverage/data/buildings --include "*.csv"
$PY coverage/prep/03_osm_roads.py
$PY coverage/prep/04_build_cells.py                              # re-run after CSVs land to fill urban layer
coverage/.venv/bin/streamlit run coverage/dashboard/app.py
```
Steps 1, 3, 4 work without GEE; step 4 leaves the urban layer empty until the building CSVs exist, then re-run it. Everything under `coverage/data/` and `*.pbf` is gitignored.

## Pipeline flow

```
acquire.py  →  downloads/<scene_id>/{B04,B03,B02,Fmask}.tif + downloads/manifest.json
process.py  →  cogs/<YYYY-MM>.tif + cogs/processed.json
upload.py   →  r2://<bucket>/<source>/<YYYY-MM>/composite.tif + r2://<bucket>/stac/catalog.json
```

Each step reads the previous step's manifest JSON — they must run in order against the same working directories. `process.py` reprojects to **EPSG:3857** so TiTiler can serve tiles without per-request reprojection. Cloud masking uses HLS Fmask bits 1–3 (cloud / adjacent cloud shadow / shadow); masked pixels become nodata = 0.

**Known bug in `acquire.py`:** The STAC search path sends `query.eo:cloud_cover.lte` which CMR STAC silently ignores, returning 0 results. Workaround: use the CMR JSON path (`search_hls_cmr`) directly, or filter cloud cover client-side after retrieval. The fallback to `search_hls_cmr` already fires when STAC returns empty, so searches work in practice.

**MVP parameters (locked 2026-05-25, see `pipeline/survey-redriver/decisions.md`):**
- AOI: MGRS T48QWJ, bbox `105.0,20.71,106.06,21.70`
- Date range: 2025-05 → 2026-05, `--max-cloud 60` (Feb 2026 skipped at 80% minimum)
- Sensors: HLS S30 + L30, least-cloudy-per-month across both
- Architecture note: TiTiler on-demand rendering is being dropped for the MVP in favour of pre-rendered static tiles stored in R2 and served via Nginx directly.

## Common commands

OSM enrichment baseline (current focus; requires `osmium`/osmium-tool + `python3` with `pyproj`):
```bash
# Full: download VN PBF (if missing) → filter tertiary+ → tally maxspeed coverage
bash osm-enrichment/baseline/run.sh

# Re-tally only, when vn-major.osm.pbf already exists
osmium export osm-enrichment/baseline/vn-major.osm.pbf -f geojsonseq --geometry-types=linestring \
  | python3 osm-enrichment/baseline/maxspeed_coverage.py
```

Pipeline (run from `pipeline/`, requires `pip install -r requirements.txt`):
```bash
# Search-only — validate AOI/dates before configuring auth
python acquire.py --aoi 105.0,20.71,106.06,21.70 --start 2025-05 --end 2026-05 --max-cloud 60 --search-only

# Full run (NASA Earthdata token or ~/.netrc for urs.earthdata.nasa.gov required)
python acquire.py --aoi 105.0,20.71,106.06,21.70 --start 2025-05 --end 2026-05 --max-cloud 60 --token <token>
python process.py --input ./downloads --output ./cogs --aoi 105.0,20.71,106.06,21.70
R2_ENDPOINT=... R2_ACCESS_KEY=... R2_SECRET_KEY=... \
  python upload.py --input ./cogs --bucket tasco-imagery-hanoi --source sentinel2 \
  --server-url https://tiles.tasco-internal.vn
```

Tile server (from `config/`, copy `.env.example` → `.env` and fill in credentials):
```bash
docker-compose up -d
docker-compose logs -f titiler
```

VPS bootstrap: `scripts/setup-vps.sh` (Docker + initial stack on fresh Vultr host).

QGIS plugin: copy `qgis-plugin/tasco_timeseries_viewer/` into the QGIS plugins directory and enable it — no build step. No automated tests.

## Working in the QGIS plugin

`plugin.py` is a single-file PyQt dock widget. When the server is unreachable it falls back silently to a **demo catalog** (monthly entries 2023-01 through 2025-05 under `sentinel2` and `planet`). Status label color signals the mode: `green` = live server, `#b58900` = demo, `red` = error.

Layer keys are `"{source}/{date}"` in `self.loaded_layers` (key → QGIS layer id). "Comparison mode" suppresses the auto-remove of the previous layer when loading a new one. XYZ URLs use literal `{x}/{y}/{z}` placeholders that QGIS expands — do not URL-encode them.

## Behavioral guidelines

### 1. Think Before Coding

Before implementing: state assumptions explicitly, surface tradeoffs, push back on over-engineered solutions. If something is unclear, stop and ask rather than guessing.

### 2. Simplicity First

Minimum code that solves the problem. No speculative features, no abstractions for single-use code, no error handling for impossible scenarios. If it could be 50 lines, don't write 200.

### 3. Surgical Changes

Touch only what the task requires. Don't improve adjacent code, comments, or formatting. Match existing style. Remove imports/variables YOUR changes made unused — but leave pre-existing dead code alone unless asked.

### 4. Goal-Driven Execution

For multi-step tasks, state a brief plan with verifiable checkpoints before starting:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```
