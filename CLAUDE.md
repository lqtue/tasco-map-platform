# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository focus

> **Strategy & docs index:** [`docs/README.md`](docs/README.md) is the **orchestrator** — north star ([`docs/vision/`](docs/vision/): TASCO Mobility Platform + official OKR 2026.06), workstream↔owner↔status, leadership-present materials ([`docs/leadership/`](docs/leadership/)), meeting minutes, and the doc index. Read it for *why* the work below exists and how it ladders to the company goal.

> **Active web surface (decided 2026-06-24):** only **two** web apps are live going forward — **`traffic/lanes/`** (the road-attribute editor, branded **"TASCO MapOps Toolkit"**) and **`traffic/sat-imagery/`** (the partner-facing satellite-imagery coverage-selection demo). Both are **published to GitHub Pages** from the `gh-pages` branch: <https://lqtue.github.io/tasco-map-platform/> → `/mapops-toolkit/` + `/sat-imagery/` + a landing page. **Everything else is archived** (`archive/`): the Streamlit dashboards (`archive/dashboards/app.py`, `traffic/maxspeed/dashboard/*`, `archive/admin-poi/coverage/dashboard/*`, the `dashboard_hub.py` launcher) and the old Vietnamese `index.html` demo are analysis/reference tools, not the worklist. The *data pipelines* that feed the sat demo are **not** archived (see `traffic/sat-imagery/` below). **Minimal refresh substrate:** both live pages are static + committed (they work with no local data), so the large gitignored data was pruned to just what *re-bakes* them — `archive/admin-poi/coverage/data/cells.parquet` + `road_coverage_cells.parquet` (sat page, via `export_static.py`) and `traffic/maxspeed/baseline/vietnam-latest.osm.pbf` (editor page, via `route_*.py`). Everything else under `coverage/data/` (building CSVs, `building_density.parquet`, intermediates) and the `vn-major`/`vn-roads` PBF extracts are deleted-but-regenerable (rclone from Drive / re-run prep / `run.sh`).

The repo is organized around the **O3 OKR** (data ops + editing app). Top-level layout:
- **`traffic/` — the live work** (O3KR1 traffic + O3KR2 sign pipelines): `maxspeed/` (baseline stats, dashboards, plans — the live problem), `signs/` (Mapillary + future GSV sign-detection pipelines → Editor DB), `lanes/` (the **"TASCO MapOps Toolkit"** SvelteKit road-attribute editor — one of the two active web apps), `sat-imagery/` (the **partner satellite-imagery coverage-selection demo** — the other active web app; static, self-contained), `signals/` (deferred stub). Start here.
- **`admin-poi/`** (O3KR1 admin + POI): `geocode/` (VN admin-boundary reverse-geocode, current + 2025 merger — self-contained dataset) and `coverage/` (H3 + Open Buildings + OSM planner — *how much satellite imagery / POI calls to buy and where*; self-contained). Each has its own section below.
- **`wiki/`** — legal-mapping reference (Thông tư 38/2024 → OSM tags), source of truth, published to Confluence. **`research/`** — scite-verified bibliography. **`PROJECT_PLAN.md`** — the enrichment proposal. **`archive/`** — deprioritized analysis tools (the Streamlit `dashboards/`, the archived `admin-poi/coverage/` and the old `index.html` demo); not the worklist.
- **`docs/`** — strategy/vision/OKR orchestrator (read `docs/README.md` first). **`scripts/`** — `confluence_publish.py` (Markdown → Confluence publisher), `md_to_html.py` (stdlib Markdown → standalone HTML + optional `--pdf` via weasyprint; passes inline `<figure>/<svg>` through verbatim, supports `**bold**`/`*italic*` — renders the vision docs/plans; needs each list item on one physical line), + `josm-imagery.xml` (JOSM custom imagery preset: loads the TASCO internal tile server as a satellite layer for editors; distribute to mappers, do not commit credentials). **`legacy/`** — the **deprioritized** satellite tile platform (`pipeline/`, `qgis-plugin/`, `config/`, `setup-vps.sh`); feature-complete for the demo, documented in the lower sections.

## Legacy: satellite tile platform (`legacy/`, deprioritized)

The original TASCO Map Platform — satellite imagery tile server and tooling for MapOps editors. Initial AOI: greater Hanoi (MGRS tile T48QWJ, bbox `105.0,20.71,106.06,21.70`). Deprioritized but feature-complete for the demo. Three independently deployable pieces:

1. **`legacy/pipeline/`** — Python CLIs: fetch HLS scenes from NASA, process into COGs, upload to R2/S3.
2. **`legacy/qgis-plugin/tasco_timeseries_viewer/`** — QGIS PyQt dock widget that loads dated imagery layers from the STAC catalog via XYZ tiles.
3. **`legacy/config/`** + **`legacy/setup-vps.sh`** — Docker Compose stack (TiTiler + Nginx) on Vultr VPS.

The three pieces share two contracts (not code imports):
- **R2 layout:** `{source}/{date}/composite.tif` (e.g. `sentinel2/2025-03/composite.tif`)
- **STAC catalog at `<server>/stac/catalog.json`:** custom shape `{"sources": {"<source>": [{"date": "YYYY-MM", "href": "<tile_url_template>", "cog_key": "..."}]}}`. The QGIS plugin also accepts standard STAC Catalog with child collection links as a fallback.

When changing either contract, update both `legacy/pipeline/upload.py::build_catalog` (producer) and `legacy/qgis-plugin/.../plugin.py::_parse_catalog` / `_parse_stac_standard` (consumer).

## Traffic data enrichment (`traffic/` — current focus)

The `traffic/` work detects and adds missing OSM attributes for Vietnam — **maxspeed**, **signalized intersections**, and **lane counts**. The live problem is maxspeed (see scope pivot); signals/lane *detection* are deferred. Cross-cutting reference docs (`wiki/`, `research/`, `PROJECT_PLAN.md`) live at the repo root; the multi-product Streamlit dashboard now lives under `archive/dashboards/` (see the active-surface note above).

> **Scope pivot (Phụng meeting 2026-06-15, `~/Downloads/MapOp Team Discuss.docx`):** the live worklist moved from **H3 cells → named national roads**. Unit of work = quốc lộ / cao tốc (motorway/trunk/primary, **≈28,000 km**); tertiary and tỉnh lộ are dropped, Hanoi center is skipped (already done). Frozen tags: **maxspeed + no-overtaking (cấm vượt) + residential-area enter/exit signs**, one tag per task (wrong street name → fix, missing → skip). **Every edit needs verifiable street-view evidence in the changeset** — bulk-copying reference speeds without it gets the changeset reverted and accounts banned; reference layers (MaxBit/maxspeed.nl, MapBox speed, the Grab-style editor) are lookup-only. Tuệ+Quân hand-edit + screen-record to build an SOP, then train ~20-30 part-time editors (paid per km) and later AI; time-per-edit is being measured to set the budget. This **supersedes the cell-based dashboard framing** below (the cell maps still run but are no longer the worklist) and the upfront 17-operator/680M plan in `traffic/maxspeed/plans/maxspeed-name-edit-plan.md`. Dashboard reworks to a **ranked road list** (by name + km, diffed vs official state km) with per-road progress.

- `PROJECT_PLAN.md` — the proposal (Vietnamese). Architecture principle threaded throughout: **AI detects, rules/graph reason** (CNN for perception; legal rules + graph inference for conclusions; manual review for conflicts). Cite **RoadTagger (He et al., 2020)** for this claim, not the plan's unverifiable "Nilsson 2024".
- `research/README.md` — scite-verified annotated bibliography (22 papers) backing the three problems, also mirrored as a References section in `PROJECT_PLAN.md`. Keep the two in sync when adding sources.
- `traffic/maxspeed/` — **the maxspeed project, self-managed in one folder** (the live problem per the scope pivot above). Holds `baseline/` (the OSM stats pipeline, below), `dashboard/` (`app_maxspeed.py` cell-map cut + `app_inspect.py` live route inspector/editor), and `plans/` (`maxspeed-name-edit-plan.md` operator deployment + budget, transcribed from the PDF alongside). Start here for maxspeed work. See `traffic/maxspeed/README.md`.
- `traffic/signs/` — the **O3KR2 sign pipeline**: build our **own** maxspeed dataset by fusing every source into one value + confidence. Two docs orchestrate it — **`SYSTEM.md`** (science-audience system explainer + progress/results) and **`README.md`** (dev how-to); read `SYSTEM.md` first. Two tracks:
  - **Track 1 — re-serve (existing):** `mapillary_signs.py` (moved from `coverage/prep/06`) pulls Mapillary's *own* pre-detected Map Features over VN → `[lat,lng,value,object_value,sign_id,first_seen,last_seen]`, speed-limit family only, into the coverage data lake (`admin-poi/coverage/data/mapillary_sign_points.parquet`). Vendor positions, partial VN accuracy.
  - **Track 2 — self-crawl → triangulate → fuse (built this cycle):** recover our **own** sign positions and merge sources. **`triangulate.py`** is the network-free geometry core reused by every source (`enu`/`enu_inv` local-meter projection, `detection_bearing` pixel→bearing, `triangulate`/`triangulate_ransac` least-squares multi-view ray intersection rejecting <5° parallax, `cluster_signs` directional-DBSCAN dedup). **`detections_pull.py`** is the Mapillary adapter + triangulation prototype (per-image detections → bearings → triangulate per `map_feature` → score vs Mapillary's published position; reuses `mapillary_signs.py` helpers, decodes detection pixel geometry via `mapbox_vector_tile`). **`compare_osm.py`** runs a whole named route (`--ref QL.51`): pull its OSM ways, crawl Mapillary along *only that corridor*, triangulate, snap each sign to the nearest OSM section, and verdict it. **`fuse.py`** is the **Bayesian fusion engine** (`P(v|obs) ∝ Prior(v)·Π L(obs|v)^w`) → per-segment value + confidence. **`inspect_map.py`** emits a standalone Leaflet HTML showing detections, bearing rays converging, the triangulated sign, and the dashed line to its matched OSM segment — the visual QA.
  - **The observation contract:** every source emits one row shape (`geom·attr·value·source·confidence·observed_at·evidence`) → fused → a `suggestion` (value+confidence). Stored as **parquet + DuckDB-spatial** today, column names mirroring the planned PostGIS `observation`/`suggestion` tables (`traffic/lanes/docs/editor-platform.html`). Architecture invariant: **AI detects, geometry/rules reason** (RoadTagger).
  - **Temporal-validity gate (critical, easy to get wrong):** a sign is only evidence if it is newer than the value it would correct, measured against **when the `maxspeed` tag value last *changed*** — read from OSM **version history** (`compare_osm.maxspeed_since_ms`/`enrich_maxspeed_age`), **not** the way's last-touch timestamp. A teammate's geometry edit (node move, way split) carries the old speed along and must not look like a fresh speed (on QL.51, 70% of ways were re-dated by this). Residual gap: split-created ways inherit maxspeed at v1 (looks "set" at split time).
  - **`fuse.py` calibration knobs** (`SOURCE_TRUST` per source, `DEFAULT_TRUST`, `CONF_TEMP`, `PRIOR_BASE`, `SIGMA_KMH`, `HALFLIFE_Y`, `SUPERSEDED_PENALTY`): the prior is deliberately **weak** (never overrides a lone explicit tag); temperature softens naive-Bayes overconfidence. These are **hand-set priors, not learned** — calibrating against ground truth is an open task. Adding a source (Waze, GSV, dashcam) = drop an observations file via `--extra SOURCE:PATH` + optionally one `SOURCE_TRUST` entry; no code-path change.
  - **Conventions:** needs `MAPILLARY_TOKEN` (client token `MLY|…`); outputs + caches go to `traffic/signs/data/` (**gitignored**) — incl. `<ref>_ways.json` (OSM geometry cache) and `<ref>_msage.json` (maxspeed-age cache), so reruns skip Overpass/history. Every non-trivial script ships a runnable check: `python3 traffic/signs/{triangulate,fuse}.py [--selfcheck]`, `detections_pull.py --selfcheck`. The bearing convention is a **calibration knob** validated on spherical (360°) cameras; the perspective/fisheye branch is untested on live data. GSV branch + residential/no-overtaking classes + a SAM3 detector (replacing Mapillary's) are still to add.
- `traffic/lanes/` — the **"TASCO MapOps Toolkit"** web app (one of the two active apps), a **SvelteKit road-attribute editor** (client-only SPA, ported from the Perl [mueschel/OSMLaneVisualizer](https://github.com/mueschel/OSMLaneVisualizer)). Despite the dir name it serves the **live maxspeed road-by-road work**: it draws a road's lanes/maxspeed/turn/signs as a schematic synced to a Leaflet map, scores length-weighted attribute completeness per road, diffs OSM km vs **official Wikidata km** (P2043), detects crossing roads, and links each segment to Mapillary/JOSM/iD for evidence. Live OSM via Overpass (no backend). Run with `npm install && npm run dev` from `traffic/lanes/`. Architecture in `traffic/lanes/CLAUDE.md`. Upstream Perl is read-only reference, **not vendored**. **Build for Pages:** `BASE_PATH=/tasco-map-platform/mapops-toolkit npm run build` → `build/`, published to `gh-pages` under `/mapops-toolkit/`. Brand text lives in `src/routes/+layout.svelte` + `src/app.html`.
- `traffic/sat-imagery/` — the **partner satellite-imagery coverage-selection demo** (the second active web app): a server-less static page (`index.html` + baked `data.js`, MapLibre + plain JS, no build). Toggle coverage layers (**Urban / Roads**, shown separately or as a union), set urban-density threshold + road-class cutoff (`Motorway…Tertiary+`) + geographic scope; the map + selected km² update live. **`data.js` is baked by `archive/dashboards/export_static.py`** (which writes straight into this folder) from the coverage parquets + baseline JSONs — that pipeline is the **refresh path and is NOT archived**. Published to `gh-pages` under `/sat-imagery/`. Relocated here from `archive/dashboards/static/` on 2026-06-24; procurement-tracking + imagery-tier/cost panels were removed at the owner's request. See `traffic/sat-imagery/README.md`.
- `traffic/signals/` — the second enrichment problem, **deferred** per the scope pivot (README stub only; no code yet, see `PROJECT_PLAN.md`). The lanes problem (#3) is also deferred as a *detection* task, but `traffic/lanes/` already ships the QA/visualization tool.
- `wiki/` (repo root) — internal legal-mapping reference (Markdown is the **source of truth**, published to Confluence): maps **Thông tư 38/2024/TT-BGTVT** → OSM tags by *road morphology, not highway class* (`01-bo-wiki-luat-internal.md`), a tag→speed-limit decision matrix + worked examples (`02-bang-quyet-dinh-theo-luat.md`), and `assets/` images. The operator reference and the stated input for the maxspeed decision tree. `internal_wiki_update_osm_v0.1.pdf` is the rendered copy.
- `archive/dashboards/` (**archived** — analysis tool, not the worklist) — the **multi-product** Streamlit decision/tracking dashboard (`app.py`): one H3 map carrying every criterion (built-up, road network with maxspeed & name coverage, islands) whose filters drive a live cost estimate, plus per-product cost tabs and a progress tracker. Reads `traffic/maxspeed/baseline/*_coverage_result.json` **and** `archive/admin-poi/coverage/data/cells.parquet` + `road_coverage_cells.parquet`. Its **`export_static.py` is still live** — it bakes the res-7 + per-province bundle (now incl. a threshold×road-class envelope grid + per-hex road class) that powers the active `traffic/sat-imagery/` demo, writing `data.js` there. `archive/dashboard_hub.py` is a Streamlit multipage launcher that runs all the archived dashboards behind one port. After the reorg, paths split: `traffic/` is at the true repo root, coverage data moved under `archive/` — `export_static.py`/`app.py` use a `TRUE_ROOT` (`parents[2]`) for the former and `REPO` (`parents[1]`) for the latter.
- `docs/STATUS_REPORT_*.md` — dated progress reports.

### Baseline pipeline (`traffic/maxspeed/baseline/`)

**`geo.py` is the shared helper module** for these scripts — `GEOD`/`line_len_m`/`feature_len_m` (geodesic WGS84 length), `MAIN_CLASSES`, `base_class`/`is_oneway`, `km`/`pct`, and the `iter_geojsonseq(stdin)` reader (RS- or newline-delimited). Every tally script imports it (resolved via Python's `sys.path[0]` = the script's own dir, so `python3 traffic/maxspeed/baseline/<x>.py` works from the repo root). Don't re-inline the geodesic/parse logic; extend `geo.py`. `prep/05` and the dashboards are separate self-contained projects and intentionally do **not** import it.

`run.sh` chains: download Geofabrik Vietnam PBF → `osmium tags-filter` to tertiary+ highways → `osmium export -f geojsonseq` → `maxspeed_coverage.py`, which tallies **geodesic (WGS84) km** per highway class and maxspeed presence via pyproj `Geod.line_length` (not projected/cartesian length — that would distort nationwide). Outputs a printed table + `maxspeed_coverage_result.json`.

Conventions baked into the analysis:
- **"tertiary+"** = `motorway, trunk, primary, secondary, tertiary` (+ `_link` variants, tallied separately). `unclassified` is excluded — in OSM it ranks *below* tertiary despite the name.
- "has maxspeed" = the *tag exists*, not that it is correct. Per-vehicle tags (`maxspeed:hgv`, `maxspeed:motorcycle`) count only toward the separate "any maxspeed*" column.
- Current result (extract 2026-06-06): tertiary+ ≈ 133,771 km, **12.9%** carry maxspeed.

`name_coverage.py` + `province_name_coverage.py` apply the same geodesic-km method to the `name` tag (nationwide and per-province → `name_coverage*_result.json`). Same "tag exists, not correct" caveat.

`morphology_coverage.py` tallies the same geodesic km but by **morphology tags** (lane count, oneway/divided carriageway, built-up) rather than maxspeed/name — because the **Thông tư 38 speed rule keys on morphology, not highway class**. It measures the slice where a law-default speed is *derivable from existing tags today* vs the slice needing satellite/street-view observation first → `morphology_coverage_result.json`.

`name_maxspeed_crosstab.py` is a one-off joint cross-tab (stdin geojsonseq): km/% by highway class × `name` presence × `maxspeed` presence → `name_maxspeed_crosstab_result.json`.

**Road-by-road tally (the 2026-06-15 scope pivot — unit of work = named national route, not cell or way):**
- `route_coverage.py` reads **OSM route relations** (`type=route, route=road, ref=QL.1`) straight from the local pbf via pyosmium (no Overpass) and, per `ref`, reports total geodesic km + maxspeed-km/%, classes spanned, member-way count, and a **connected-component count** (union-find on endpoint nodes; 1 = one continuous route, >1 = gaps/disjoint). Because OSM models divided highways as two one-way carriageways (~1.5–2× centerline), it also reports a **centerline estimate** = `bidirectional_km + oneway_km/2` — compare *that*, not member km, to official road-length stats → `route_coverage_result.json`. This is the relation-based answer; `_byroad.py` is the older stdin/geojsonseq version that groups by the `ref`/`name` *tag* on individual ways (misses ref-less ways, can't detect network connectivity) — kept for name-based grouping, largely superseded by `route_coverage.py`.
- `route_geom.py` emits per-(ref, member way) **geometry + current tags** (`maxspeed`, `lanes`, `divided` morphology hint, `oneway`, path) for the inspector/editor to draw a route on a map → `route_geom.parquet` (regenerable, **gitignored**).
- `route_freshness.py` emits a compact per-route **speed profile + edit freshness** for the `traffic/lanes/` dashboard sparkline: walks member ways in relation order, bins into 60 equal-count buckets of `[maxspeed_code, age_days]` (age from OSM `timestamp` — only the PBF has it), plus a length-weighted median edit-age → `route_freshness.json` (~220 KB; **copy into `traffic/lanes/static/data/`** alongside `route_coverage_result.json`→`route_coverage.json`, which the dashboard fetches).
- `route_map.py` emits a simplified national-network **GeoJSON** (QL + CT only, Douglas-Peucker via shapely) with per-segment `{ref, ms, age}` for the `traffic/lanes/` `/map` overview (recolour by coverage / speed / freshness) → `national_roads.geojson` (~6 MB; **copy into `traffic/lanes/static/data/`**).

The `dashboard/` for maxspeed holds two Streamlit apps: `app_maxspeed.py` (the cell-map cut, above) and **`app_inspect.py`** — a **live OSM route inspector + local maxspeed editor** (render.pl-style): fetches a route by ref from **Overpass live**, draws member ways colored by maxspeed presence, and lets an operator stage proposed `maxspeed`/`lanes`/`median` tags to a **local** worklist `dashboard/data/route_edits.json` (**gitignored**; nothing is written to OSM — operators apply staged edits in iD with street-view evidence per the scope pivot).

The `.pbf` files (`vietnam-latest.osm.pbf` ~309 MB, `vn-major.osm.pbf`, `vn-roads.osm.pbf`) are large regenerable artifacts — do **not** commit them. `.gitignore` already covers `*.pbf` and all of `admin-poi/coverage/data/`.

## Vietnam Imagery-Coverage Planner (`admin-poi/coverage/`)

Decides **how much satellite imagery to buy and where**. Tiles Vietnam with the Uber **H3** grid (res 10) **only around three targets** — urban/built-up, strategic highways (operational + under construction), islands — attaches per-cell evidence, and ships a **Streamlit + pydeck** dashboard where thresholds are *live filters* and total **km²** (and cost = km² × $/km²) update instantly. Nothing is baked in: the team tries criteria and reads the resulting buy-envelope.

**Core architecture — a 4-step prep chain produces ONE contract, `data/cells.parquet`, that the dashboard consumes.** Each `prep/0N_*.py` writes a parquet the next step reads; `dashboard/app.py` only ever loads `cells.parquet` (+ `cells_res9.parquet`). The pipeline is **sparse by design** — candidate cells are generated only around targets (~5M res-10 cells), never the whole country. Three scripts sit outside the 4-step spine: `prep/05_road_coverage.py` (a sidecar, below), `prep/02b_gee_building_polygons.py` (a variant of step 2, below), and `prep/07_building_density.py` (a POI-sizing sidecar, below). The old `prep/06_mapillary_signs.py` **moved to `traffic/signs/mapillary_signs.py`** (see the traffic section) — only its output parquet is still consumed here.

- `prep/01_admin.py` → `data/admin_wards.parquet` `[ma, province, ward, loai, is_island, geometry]`. Source: `~/Downloads/VietnamWardBoundary2025.geojson` (already EPSG:4326). **Islands = `loai == "đặc khu"`** (13 special zones); provinces = `tentinh` (34), wards = `tenhc` (3321). Asserts those counts.
- `prep/02_gee_buildings.py` → launches **34 per-province Earth Engine exports** of Open Buildings v3 centroids (`confidence ≥ 0.65`) as `{lon,lat,area}` CSV to Drive folder `OB_VN_BUILDINGS`. **Why centroids, not a raster, and why per-province:** a 10 m built-up raster of Vietnam is ~10⁹ px; sparse centroids are compact and let H3 assignment happen locally. **GEE has no native H3** — this is the whole reason assignment is deferred to step 4.
- `prep/02b_gee_building_polygons.py` → same export but keeps the full building **footprint polygon** + `area_in_meters` + `confidence` as GeoJSON to Drive folder `OB_VN_POLYGONS`. This is **not** part of the coverage pipeline (centroids are enough for H3 counting) — it exists to ship footprints to the backend for **POI-crawl dedup** (point-in-polygon: POIs in the same footprint are duplicate candidates). Polygon GeoJSON is ~5× the centroid CSV; convert to GeoParquet with **DuckDB spatial** (`ST_Read` → `COPY … (FORMAT parquet)`) since homebrew GDAL/pyogrio Parquet are broken here. EE may create **multiple Drive folders with the same name** — fetch by folder-id, not name. `--only "prov1,prov2"` runs a subset.
- `prep/03_osm_roads.py` → `data/roads.parquet` `[class, status, geometry]` via `osmium tags-filter` on `traffic/maxspeed/baseline/vietnam-latest.osm.pbf`. Also derives `data/island_land.parquet` by polygonizing OSM `natural=coastline` and intersecting with đặc khu zones.
- `prep/04_build_cells.py` → unions the three sources into `data/cells.parquet` (one row per `h3_id`) + a `cells_res9.parquet` rollup. **Urban assignment uses DuckDB's `h3` community extension** (`h3_latlng_to_cell_string(lat,lon,10)`) over the building CSVs — this produces **identical ids to python `h3`**, so DuckDB (fast, for millions of points) and python-h3 (roads/islands) interoperate. `_monitor.py` is a throwaway EE task-state poller.
- `prep/05_road_coverage.py` → `data/road_coverage_cells.parquet` `[h3_id, road_km, maxspeed_km, name_km, lanes_km, top_class]` — a **sidecar**, not part of the `cells.parquet` contract. For each res-10 cell it tallies geodesic km of tertiary+ road and how many of those km already carry maxspeed/name/lanes tags, so the **`archive/dashboards/` app** can light up the gap on the same hexes. Reads an `osmium export -f geojsonseq` stream on **stdin** (the tertiary+ extract, whose tags survive — unlike `roads.parquet`, which dropped them). Reuses the segmentize+H3 binning from step 4 and geodesic length (pyproj `Geod`) from the baseline scripts.
- `prep/07_building_density.py` → `data/building_density.parquet` `[h3_11, h3_10, h3_9, province, n_buildings, built_area_m2]` — a **POI-sizing sidecar** (not part of the `cells.parquet` contract). Aggregates the Open Buildings centroid CSVs to **res-11** H3 via DuckDB's `h3` extension, **pre-computing the res-10/res-9 parent ids** so the POI dashboard rolls up to any resolution without re-reading the 3.4 GB of CSVs; province is joined from `cells.parquet` (res-10 parent). Self-checks the total building count against `EXPECTED_BUILDINGS`. Consumed by `dashboard/app_poi.py` (below), **not** by `dashboard/app.py`.
- (The street-view sign sidecar that used to be `prep/06_mapillary_signs.py` now lives at `traffic/signs/mapillary_signs.py`; its `data/mapillary_sign_points.parquet` output is still read by the dashboards. See the traffic section for it.)

**Two dashboards in `dashboard/`:** `app.py` is the coverage/buy-envelope dashboard (loads `cells.parquet`); **`app_poi.py`** is the separate **AWS reverse-geocode H3-resolution sizing** dashboard (loads `building_density.parquet`) — it finds the coarsest H3 res whose cells stay under AWS's 50-result `SearchPlaceIndexForPosition` cap (uniform vs adaptive top-down res-9→10→11), with a live cost estimate. This is the implementation of the POI-crawl methodology section below.

**`cells.parquet` schema (the prep↔dashboard contract):** `h3_id, built_up_area_m2, building_count, road_built, road_built_class, road_construction, road_constr_class, is_island, is_island_land, cell_area_m2, built_up_ratio (clipped [0,1]), res9_id, lat, lng, province, ward`. The dashboard's selection rule = **union of any enabled criterion**, intersected with the province filter; category km² breakdowns intentionally overlap.

**Island maritime-inflation gotcha:** đặc khu admin polygons enclose large open sea (Trường Sa ≈ 4,360 km² of mostly water), so full-zone island area (~6,370 km²) massively overstates land. `is_island_land` (OSM-coastline-derived, ~867 km²) is the honest extent; the dashboard exposes both as a **"Island extent" radio**. When touching island logic, keep both flags.

**Conventions:** canonical Uber H3 v4 ids, **res 10** (~16,470 m²/cell), `res9_id` parent for zoom-out. Roads: `highway` ∈ {motorway, trunk, primary} (+`_link`); `built` = operational tag, `building` = `highway=construction` with matching `construction` tag. Urban threshold (`built_up_ratio`) is a **slider, never hard-coded** — default 10% ≈ "core built-up"; "any building" catches rural farm structures and is ~5× larger, so don't quote it as urban.

**Environment (matches repo-wide gotchas):** dedicated venv at `admin-poi/coverage/.venv` on **python3.13** (not 3.14 — PEP 668 + missing wheels). **`fiona` is broken** (GDAL dylib mismatch) → read GPKG/GeoJSON via geopandas/pyogrio only. Step 2 needs an **Earth Engine Cloud project** (`EE_PROJECT=<id>`); the project in use is `propane-avatar-430409-r2`.

**Retrieving the building CSVs from Drive (~3.4 GB, 34 files):** an **rclone `gdrive:` remote** (read-only OAuth) is configured — `rclone copy gdrive:OB_VN_BUILDINGS admin-poi/coverage/data/buildings --include "*.csv"`. The MCP Google Drive `download_file_content` tool is **not** usable here: it returns base64 into context and these files are 50–280 MB each. Do **not** use stored Earth Engine credentials to hit the Drive API for this (a safety classifier blocks credential enumeration). CSVs are transient — after step 4 aggregates them they can be deleted (they persist in Drive and locally enable re-aggregation at a different H3 resolution without re-download).

**Run it:**
```bash
PY=admin-poi/coverage/.venv/bin/python
$PY admin-poi/coverage/prep/01_admin.py
EE_PROJECT=<id> $PY admin-poi/coverage/prep/02_gee_buildings.py            # launch exports; --monitor to poll
rclone copy gdrive:OB_VN_BUILDINGS admin-poi/coverage/data/buildings --include "*.csv"
$PY admin-poi/coverage/prep/03_osm_roads.py
$PY admin-poi/coverage/prep/04_build_cells.py                              # re-run after CSVs land to fill urban layer
admin-poi/coverage/.venv/bin/streamlit run admin-poi/coverage/dashboard/app.py
```
Steps 1, 3, 4 work without GEE; step 4 leaves the urban layer empty until the building CSVs exist, then re-run it. Everything under `admin-poi/coverage/data/` and `*.pbf` is gitignored.

## AWS POI Reverse-Geocode Crawl (`admin-poi/coverage/` — methodology)

Strategy for building the Vietnam address + POI database via AWS `SearchPlaceIndexForPosition`. The analysis lives in `admin-poi/coverage/data/` (fully gitignored — local working area).

**Core constraint:** AWS returns at most **50 results** per query, sorted by proximity. In dense urban areas those 50 results cover only ~28 m — buildings at cell edges are missed. The resolution strategy is **recursive**: query at H3 res-11 first; if a cell saturates (>9 OB buildings, implying >50 places), subdivide to 7 res-12 children; if a res-12 child saturates (large mall / tower, place density >~159,000 places/km²), subdivide to res-13. Current cost estimate: **~$12,762** for Vietnam-wide (25.5M calls at $0.50/1k).

**Key calibration numbers (from D4 HCM field sample, Khanh Hội ward):**
- 4.6× places per Open Buildings footprint in ultra-dense tube-house areas → res-12 threshold = 9 buildings/cell
- 73.1% of places are visible from only one cell → missed if that cell truncates
- 29.1% duplicate rate across overlapping cells; dedup key = AWS `place_id`
- **Sample ceiling is res-11.** Whether res-12 itself saturates inside large commercial buildings is unverified — run a ~$0.05 spot-check (50 res-12 cells inside a Vincom mall) before bulk run.

**Improving the threshold:** `area_in_meters` from Open Buildings is a free height proxy (`estimated_floors = max(1, sqrt(area_m² / 50))`). Cross with OSM `building:levels` from the Vietnam PBF for the ~20–30% of large Hanoi/HCM buildings that carry it. Biljecki et al. (2016, PLOS ONE) confirms volume-based approaches outperform flat footprint count for morphologically heterogeneous areas.

**Report generation:** `admin-poi/coverage/data/build_report.py` (gitignored) — generates all charts via matplotlib + exports PDF via weasyprint (`pip3 install weasyprint --break-system-packages`). Run from `admin-poi/coverage/data/`.

## VN Admin Geocode dataset (`admin-poi/geocode/`)

Self-contained **source-of-truth** dataset for reverse-geocoding a coordinate to its **current** and **past** Vietnam admin name (the 2025 province/ward merger). `geocode.py` does point-in-polygon independently on each layer; serving infra (H3/precompute) is intentionally left out.

- Data lives under `admin-poi/geocode/data/` (**gitignored**, ~150 MB): `admin_current.parquet` (3,321 post-merger wards, 34 provinces), `admin_past.parquet` (pre-merger units, clean partition — a coord matches exactly one), `crosswalk.parquet` (past↔current overlap mapping). Code/docs (`geocode.py`, `MANIFEST.json`, `README.md`, `requirements.txt`, `osm_validation_flags.csv`) are tracked at the module root. **`geocode.py` reads `data/*.parquet`** — keep that path if you move files.
- **Key gotcha:** join/key on `current_id` (official 2025 code), never on raw `matinhxa` (13 HCMC collisions). OSM carries no official 2025 code → enrichment joins by name+geometry, not code. All 13 đặc khu (island special zones) have a past record; far-offshore open water can be null on both layers (correct, not a bug). `README.md` documents the full schema + data-quality audit.
- Run: `pip install -r admin-poi/geocode/requirements.txt && python3 admin-poi/geocode/geocode.py [lat lon]...`

## Confluence publishing (`scripts/confluence_publish.py`)

Publishes repo Markdown (the source of truth) to Confluence Cloud at **tascomaps.atlassian.net**. Stdlib-only (no pandoc): Markdown → Confluence *storage* XHTML, uploads images in `assets/` as page **attachments** (the Atlassian MCP can't do attachments — use this script for image-heavy pages), idempotent page upsert (create or new version).

- Per-page target **space key** + parent nesting are declared in the `PAGES` manifest in the script (currently: wiki/matrix/plan → `NR`, geocode README → `GSPA`). Edit `PAGES` to add pages.
- Auth = HTTP Basic `CONFLUENCE_EMAIL:CONFLUENCE_TOKEN` (Atlassian API token) + `CONFLUENCE_BASE_URL`. Env vars don't persist across shells — pass them inline on the run command. `--dry-run` prints the storage XHTML and image list without any network call.
- The built-in Markdown converter handles the constructs these docs use (headings, GFM tables with `<br>` cells, lists, blockquotes, inline code/bold/italic/links, standalone images); validate new pages with `--dry-run` + an XML well-formedness check before publishing.

## Pipeline flow

```
acquire.py  →  downloads/<scene_id>/{B04,B03,B02,Fmask}.tif + downloads/manifest.json
process.py  →  cogs/<YYYY-MM>.tif + cogs/processed.json
upload.py   →  r2://<bucket>/<source>/<YYYY-MM>/composite.tif + r2://<bucket>/stac/catalog.json
```

Each step reads the previous step's manifest JSON — they must run in order against the same working directories. `process.py` reprojects to **EPSG:3857** so TiTiler can serve tiles without per-request reprojection. Cloud masking uses HLS Fmask bits 1–3 (cloud / adjacent cloud shadow / shadow); masked pixels become nodata = 0.

**Known bug in `acquire.py`:** The STAC search path sends `query.eo:cloud_cover.lte` which CMR STAC silently ignores, returning 0 results. Workaround: use the CMR JSON path (`search_hls_cmr`) directly, or filter cloud cover client-side after retrieval. The fallback to `search_hls_cmr` already fires when STAC returns empty, so searches work in practice.

**MVP parameters (locked 2026-05-25, see `legacy/pipeline/survey-redriver/decisions.md`):**
- AOI: MGRS T48QWJ, bbox `105.0,20.71,106.06,21.70`
- Date range: 2025-05 → 2026-05, `--max-cloud 60` (Feb 2026 skipped at 80% minimum)
- Sensors: HLS S30 + L30, least-cloudy-per-month across both
- Architecture note: TiTiler on-demand rendering is being dropped for the MVP in favour of pre-rendered static tiles stored in R2 and served via Nginx directly.

## Common commands

OSM enrichment baseline (current focus; requires `osmium`/osmium-tool + `python3` with `pyproj`):
```bash
# Full: download VN PBF (if missing) → filter tertiary+ → tally maxspeed coverage
bash traffic/maxspeed/baseline/run.sh

# Re-tally only, when vn-major.osm.pbf already exists
osmium export traffic/maxspeed/baseline/vn-major.osm.pbf -f geojsonseq --geometry-types=linestring \
  | python3 traffic/maxspeed/baseline/maxspeed_coverage.py
```

Pipeline (run from `legacy/pipeline/`, requires `pip install -r requirements.txt`):
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

Tile server (from `legacy/config/`, copy `.env.example` → `.env` and fill in credentials):
```bash
docker-compose up -d
docker-compose logs -f titiler
```

VPS bootstrap: `legacy/setup-vps.sh` (Docker + initial stack on fresh Vultr host).

QGIS plugin: copy `legacy/qgis-plugin/tasco_timeseries_viewer/` into the QGIS plugins directory and enable it — no build step. No automated tests.

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
