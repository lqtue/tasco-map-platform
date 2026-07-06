# Data Partnership Brief — Satellite Imagery
**TASCO Mapping Division** · Issued 2026-06-25 · Confidential

---

<!--
  TEMPLATE NOTE (internal):
  Sections marked [FIXED] are identical across all data-type briefs.
  Sections marked [SWAPPABLE] are replaced per partner type.
  To create a brief for POI / Street View / Traffic / Digital Twins,
  duplicate this file and replace every [SWAPPABLE] block.
-->

## About TASCO  [FIXED]

**TASCO Mapping Division** is the geospatial data and navigation arm of **TASCO Group**, Vietnam's leading transportation conglomerate with approximately 10,000 employees and operations spanning toll infrastructure, transit, and mobility services. TASCO's technology subsidiary, **VTII**, develops and operates the platform stack that the Mapping Division's data feeds.

Through **VETC**, HUT operates **75% of Vietnam's Electronic Toll Collection (ETC) network** — 4.2 million registered vehicle owners and over 2 million toll transactions processed daily across the national highway system.

## What We Are Building  [FIXED]

We are building **Vietnam's first self-owned, daily-fresh, legally clean national map platform** — purpose-built for real-time driver assistance, logistics, and ADAS.

**Core products:**
- **V-Base-Maps** — a daily-updated national road graph (OSM-based) enriched with AI-detected attributes: speed limits, lane counts, traffic signs, and road morphology
- **V-Navigation-Maps** — turn-by-turn routing with *just-in-time* lane-level alerts (speed limit warnings, lane-change guidance, enforcement camera positions) delivered *before* the driver needs to act

**Data architecture:** OpenStreetMap and Overture Maps as the base graph, enriched continuously by our MapOps editor team using AI-proposed attributes validated against satellite imagery, street-view evidence, and Vietnamese traffic law (Thông tư 38/2024). Derivative products serve our consumer navigation app (MyTasco), VETC fleet management, and B2B logistics partners.

**Why we build rather than buy:** existing commercial map providers either prohibit use on competing surfaces (Google), carry stale road geometries (TomTom, 2–3 years behind), or lack the attribute depth needed for lane-level guidance. Building on OSM gives us a legally clean, self-owned foundation that we control.

---

## Why We Need Satellite Imagery  [SWAPPABLE]

Our speed-limit enrichment pipeline assigns legal default speeds from Vietnamese traffic law, but those defaults depend on road morphology — specifically, whether a segment runs through a *built-up area* (khu dân cư). OSM currently classifies fewer than 30% of Vietnam's road network with sufficient morphology tags to derive this automatically.

Satellite imagery fills three gaps we cannot resolve from any other source. A practical constraint on acquisition: Vietnam's monsoon season (May–October in the north; October–January in the south) produces heavy cloud cover over much of the country simultaneously, making guaranteed single-date cloud-free coverage of the full AOI unfeasible. We expect mosaics composed from multiple acquisition dates; a clear re-acquisition policy for cloud-rejected scenes is therefore a key evaluation criterion.

The four gaps:

1. **Urban boundary detection** — identify built-up extents to assign the correct legal speed default (~50 km/h urban vs. 80–100 km/h rural) across 116,498 km of road currently missing a maxspeed tag.
2. **AI geometry extraction** — U-Net++ segmentation of road surfaces, building footprints, and natural features (rivers, vegetation) from imagery, used to auto-generate and validate road geometry in provinces where OSM community editing is sparse or out of date.
3. **Road network verification** — cross-check OSM topology against imagery to detect missing segments, misaligned geometries, and construction-stage roads before they enter the routing graph.
4. **Maritime territory coverage** — Vietnam's strategic island territories (Trường Sa, Hoàng Sa and other archipelagos) have zero street-view accessibility; satellite is the only viable source for road and infrastructure mapping there.

---

## Technical Requirements — Satellite Imagery  [SWAPPABLE]

### Coverage

| Priority tier | Description | Approximate area |
|---|---|--:|
| **P1 — Urban built-up** | Built-up zones around Vietnam's cities and towns | ~15,355 km² |
| **P2 — Road corridors** | 10 km buffer along national roads (motorway, trunk, primary) | ~5,662 km² |
| **P3 — Maritime territories** | Strategic island territories (Trường Sa, Hoàng Sa archipelagos) | ~867 km² |
| **Total initial envelope** | Union of P1–P3 (overlaps removed) | **~20,350 km²** |

Geographic scope: Socialist Republic of Vietnam (territorial land + recognised maritime territories). Coordinate reference system: WGS84 (EPSG:4326).

### Image Specifications

| Parameter | Requirement | Notes |
|---|---|---|
| **Ground Sample Distance (GSD)** | ≤ 0.5 m | Sub-metre preferred for building footprint and road-edge precision |
| **Spectral bands** | RGB minimum; Pansharpened or multispectral preferred | NIR useful for vegetation/built-up separation |
| **Cloud cover** | ≤ 30% per scene (≤ 15% preferred) | Cloud-free for island acquisitions; see seasonal note below |
| **Off-nadir angle** | ≤ 25° preferred | Higher angles accepted for islands only |
| **Geometric accuracy** | CE90 ≤ 5 m absolute | Sufficient for OSM overlay; sub-1 m not required |
| **Acquisition age** | ≤ 18 months from delivery date | For initial buy; fresher preferred for P1 |
| **Revisit / update** | Minimum 1× per year per AOI for ongoing contract | Quarterly preferred for urban zones |

### Delivery

| Parameter | Requirement |
|---|---|
| **Format** | Cloud-Optimized GeoTIFF (COG) |
| **Tiling** | Tiled internally (256 × 256 px or 512 × 512 px); overview levels included |
| **Delivery mechanism** | S3-compatible object storage (our bucket or staging bucket with transfer) |
| **Catalog** | STAC-compatible catalog (standard or custom) preferred; minimum = manifest JSON per delivery batch |
| **Metadata** | Per-scene: acquisition date, cloud cover %, sensor ID, off-nadir angle |
| **Lead time** | Archive delivery ≤ 5 business days; new tasking ≤ 8 weeks from order |
| **Cloud QC & re-acquisition** | Scenes exceeding the cloud cover threshold are replaced at no additional charge; re-delivery timeline to be agreed in contract |

---

## What We Are Looking For from Partners  [SWAPPABLE]

We are evaluating providers for both an **initial bulk acquisition** (the ~20,350 km² envelope above) and an **ongoing annual update** contract. We welcome proposals addressing either or both.

Specifically, we ask for:

1. **Capability statement** — sensor fleet, resolution range, revisit frequency over Vietnam, archive depth (how far back does historical imagery go for our AOIs?)
2. **Archive inventory** — before we commit to new tasking, we ask for an inventory of existing archive coverage over our AOI at ≤ 0.5 m GSD and ≤ 18 months age; archive acquisition is preferred where it meets spec (faster delivery, lower cost)
3. **Pricing model** — per km² pricing broken down by: archive vs. new tasking, cloud QC rejection and re-acquisition cost (free re-fly or charged again?), minimum order quantity, and volume tiers; we are evaluating a ~20,350 km² initial buy and an ongoing annual update
4. **Sample imagery** — one urban AOI (suggest: central Hanoi or central Ho Chi Minh City, ~50 km²) and one national road corridor segment (~100 km of QL1 central Vietnam) for internal evaluation before contract
5. **Delivery timeline** — lead time from order to delivery for the initial envelope; guaranteed % of AOI delivered cloud-free and re-acquisition SLA for rejected scenes
6. **Licensing terms** — we require: (a) commercial use in our navigation products; (b) right to create derivative works (vector data, map tiles, enriched road attributes) extracted from the imagery; (c) redistribution of those derivative products to end-users (consumers, fleet operators, B2B partners) without disclosing the imagery source; (d) no mandatory attribution of the imagery provider in our end-user products; (e) sub-licensing rights if we supply derived map data to third parties

---

## Contact

**Lê Quang Tuệ** — Data & Partnerships, TASCO Mapping Division
lequangtuevn@gmail.com

*This brief is confidential and intended solely for the recipient organisation.*
