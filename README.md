# TASCO Map Platform

MapOps data-ops + editing work for the **O3 OKR** (traffic data, admin/POI, and the pipelines
that feed the Editor Spatial DB). The repo is organized by the data domains the team works in;
the original satellite tile platform is parked under `legacy/`.

> Strategy, OKRs and meeting minutes live in [`docs/`](docs/) — start at [`docs/README.md`](docs/README.md).
> Agent/architecture guidance is in [`CLAUDE.md`](CLAUDE.md).

> **Live apps (the two active web surfaces):** **MapOps Toolkit** (road-attribute editor, `traffic/lanes/`)
> and the **Satellite Imagery coverage-selection demo** (`traffic/sat-imagery/`) — published to GitHub Pages
> at <https://lqtue.github.io/tasco-map-platform/>. Everything under `archive/` (incl. the Streamlit
> dashboards) is deprioritized reference.

## Structure

```
tasco-map-platform/
├── traffic/              ← live work: traffic data + sign pipelines (O3KR1.1, O3KR2)
│   ├── maxspeed/         OSM maxspeed: baseline stats, dashboards, operator plans (THE live problem)
│   ├── signs/            sign-detection pipelines → Editor DB (Mapillary now; GSV later)
│   ├── lanes/            ACTIVE WEB APP — "TASCO MapOps Toolkit" SvelteKit road-attribute editor
│   ├── sat-imagery/      ACTIVE WEB APP — satellite-imagery coverage-selection demo (static; data.js baked)
│   └── signals/          signalized-intersection detection (deferred stub)
├── admin-poi/            ← admin boundaries + POI (O3KR1.2)
│   ├── geocode/          VN admin reverse-geocode dataset (current + 2025 merger)
│   └── coverage/         H3 + Open Buildings + OSM planner (imagery / POI-call budget)
├── wiki/                 legal-mapping reference: Thông tư 38/2024 → OSM tags (→ Confluence)
├── research/             scite-verified annotated bibliography
├── PROJECT_PLAN.md       the enrichment proposal (3 problems: maxspeed, signals, lanes)
├── docs/                 strategy · vision · OKR · leadership · minutes · status reports
├── scripts/              confluence_publish.py (+ josm-imagery.xml)
├── archive/              deprioritized: Streamlit dashboards (+ export_static.py, still bakes sat-imagery/data.js)
└── legacy/               deprioritized satellite tile platform (pipeline, qgis-plugin, config, setup-vps.sh)
```

## Where to start

| You want to… | Go to |
|---|---|
| Maxspeed coverage stats / road-by-road tally | `traffic/maxspeed/baseline/` (`run.sh`, `route_coverage.py`) |
| QA / edit a road's attributes (MapOps Toolkit) | `traffic/lanes/` |
| Show partners the imagery coverage-selection demo | `traffic/sat-imagery/` |
| Pull street-view speed signs | `traffic/signs/mapillary_signs.py` |
| Reverse-geocode a coordinate (VN admin) | `admin-poi/geocode/` |
| Decide imagery / POI-call budget by area (archived dashboards) | `admin-poi/coverage/` + `archive/dashboards/` |
| Legal speed-limit rules → OSM tags | `wiki/` |
| The satellite tile server (legacy) | `legacy/` |

Each module has its own `README.md` (and `traffic/maxspeed/`, `traffic/lanes/` carry deeper notes).
Run commands and cross-module data contracts are documented in [`CLAUDE.md`](CLAUDE.md).
