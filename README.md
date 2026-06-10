# TASCO Map Platform — Founding Team Package

Everything for the first 30 days: role documentation, satellite imagery tile server MVP, and QGIS tooling.

## Structure

```
tasco-map-platform/
├── README.md                          ← you are here
├── docs/
│   ├── JD_Map_Operation_Engineer.docx            # MapOps JD (other engineer, for offer letter)
│   ├── JD_Geospatial_Data_Analyst.docx           # Your counter-proposal JD
│   ├── TASCO_Map_Team_Role_Analysis.docx         # Briefing for Phụng on role differentiation
│   └── MVP_Sat_Imagery_Tile_Server_Hanoi.md      # Full MVP plan
├── pipeline/
│   ├── acquire.py                     # Search & download HLS scenes from NASA CMR
│   ├── process.py                     # Cloud mask, composite, clip, convert to COG
│   ├── upload.py                      # Upload COGs to R2/S3, update STAC catalog
│   ├── catalog.py                     # Generate/update STAC catalog JSON
│   └── requirements.txt
├── qgis-plugin/
│   └── tasco_timeseries_viewer/
│       ├── __init__.py
│       ├── metadata.txt
│       ├── plugin.py                  # Main plugin: dock panel, date browser, layer loader
│       ├── icon.png
│       ├── example_catalog.json       # API contract for tile server
│       └── README.md
├── config/
│   ├── titiler.Dockerfile             # TiTiler container for Vultr VPS
│   ├── docker-compose.yml             # TiTiler + Nginx stack
│   ├── nginx.conf                     # Reverse proxy with tile caching
│   └── .env.example                   # Environment variables template
└── scripts/
    ├── setup-vps.sh                   # Bootstrap Vultr VPS with Docker + TiTiler
    └── josm-imagery.xml               # JOSM custom imagery entry for the tile server
```

## Quick Start

### 1. Set up the tile server (Vultr VPS)

```bash
cp config/.env.example config/.env
# Edit .env with your R2/S3 credentials and server URL
cd config && docker-compose up -d
```

### 2. Run the acquisition pipeline

```bash
cd pipeline
pip install -r requirements.txt
# Search for HLS scenes over Hanoi, last 6 months, <20% cloud
python acquire.py --aoi 105.75,20.95,105.90,21.10 --start 2025-01 --end 2025-06 --max-cloud 20
# Process and upload
python process.py --input ./downloads --output ./cogs
python upload.py --input ./cogs --bucket tasco-imagery-hanoi
```

### 3. Install the QGIS plugin

Copy `qgis-plugin/tasco_timeseries_viewer/` to your QGIS plugins directory and enable it.

### 4. Install recommended third-party QGIS plugins

For ad-hoc exploration and analysis (not daily editing):
- [NASA Earthdata](https://github.com/opengeos/qgis-nasa-earthdata-plugin) — search & stream HLS directly
- [GEE Data Catalogs](https://github.com/opengeos/qgis-gee-data-catalogs-plugin) — Earth Engine access
- [OpenGeoAgent](https://github.com/opengeos/GeoAgent) — AI-assisted analysis

### 5. Connect JOSM

Import `scripts/josm-imagery.xml` into JOSM via **Imagery → Imagery preferences → Add from file**.

## Architecture

```
NASA CMR / Earthdata ──acquire.py──▶ Local downloads
                                          │
                                    process.py (cloud mask, composite, COG)
                                          │
                                    upload.py ──▶ Cloudflare R2 (zero egress)
                                                      │
                                                 TiTiler (Vultr VPS)
                                                      │
                                                 Nginx (cache + auth)
                                                      │
                                    ┌─────────────────┼─────────────────┐
                                    │                 │                 │
                              QGIS Plugin      JOSM TMS layer    Web viewer
                           (MapOps editing)   (MapOps editing)   (QA / demo)
```

## Key Decisions

- **R2 over S3** for tile storage: zero egress fees, S3-compatible API
- **TiTiler over pre-rendered tiles**: dynamic rendering from COGs, simpler for small team
- **HLS over raw Sentinel-2**: harmonized Landsat+Sentinel, better temporal coverage
- **NASA Earthdata plugin for exploration, R2 mirror for production**: low-latency daily editing from mirrored data, ad-hoc analysis against NASA source
- **STAC from day one**: even as a flat JSON file, ensures future compatibility
