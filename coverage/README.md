# Vietnam Satellite-Imagery Coverage Planner

Decide **how much imagery to buy and where**: tile Vietnam with the Uber **H3** grid
(res 10) only around targets — **urban/built-up**, **strategic highways** (built +
under-construction), and **islands** — then explore criteria in a dashboard that shows
total **km²** and estimated **cost** live.

## Setup
```bash
python3.13 -m venv coverage/.venv
coverage/.venv/bin/pip install -r coverage/requirements.txt
```

## Pipeline (run from repo root, with the venv python)
```bash
PY=coverage/.venv/bin/python

# 1. Admin + islands  (source: ~/Downloads/VietnamWardBoundary2025.geojson)
$PY coverage/prep/01_admin.py            # -> data/admin_wards.parquet  (34 prov, 13 đặc khu)

# 2. Open Buildings via GEE  (needs an Earth Engine Cloud project)
EE_PROJECT=<id> $PY coverage/prep/02_gee_buildings.py            # launch 34 Drive exports
EE_PROJECT=<id> $PY coverage/prep/02_gee_buildings.py --monitor  # poll
#   then download the Drive folder OB_VN_BUILDINGS into coverage/data/buildings/

# 3. OSM highways  (source: osm-enrichment/baseline/vietnam-latest.osm.pbf)
$PY coverage/prep/03_osm_roads.py        # -> data/roads.parquet  (built / building)

# 4. Assemble master cell table
$PY coverage/prep/04_build_cells.py      # -> data/cells.parquet + data/cells_res9.parquet

# 5. Dashboard
coverage/.venv/bin/streamlit run coverage/dashboard/app.py
```
Steps 1, 3, 4 work without GEE; step 4 simply leaves the urban layer empty until the
building CSVs from step 2 are present, then re-run step 4.

## Conventions
- **H3:** canonical Uber H3 v4, **res 10** (~16,470 m²/cell); `res9_id` parent stored for zoom-out.
- **Urban:** `built_up_ratio = built_up_area / cell_area`; threshold is a live slider (not baked in).
- **Roads:** `highway` ∈ {motorway, trunk, primary} (+_link). `built` = operational tag; `building` = `highway=construction` with matching `construction` tag.
- **Islands:** `loai == "đặc khu"` (13 special zones). ⚠️ Their admin polygons enclose large
  **maritime** area (e.g. Trường Sa ≈ 4,360 km² of mostly sea), which inflates the island km².
- **Admin:** province = `tentinh` (34), ward = `tenhc` (3321); attached per cell by point-in-polygon.

## Outputs (gitignored under `data/`)
`admin_wards.parquet`, `roads.parquet`, `buildings/*.csv`, `cells.parquet`, `cells_res9.parquet`.
