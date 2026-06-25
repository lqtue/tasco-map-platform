# Technical Requirements — Satellite Imagery
**TASCO Mapping Division** · 2026-06 · Confidential · *Follows Part 1 — Introduction*

---

## Area of Interest (AOI)

Our coverage requirements are calculated from a live H3 hexagonal grid model of Vietnam's road network and urban built-up areas. The interactive version is available at:

**https://lqtue.github.io/tasco-map-platform/sat-imagery/**

From that page you can:
- Visualise our target cells by type (urban / road corridor / combined)
- Adjust density and road-class thresholds to see how the envelope changes
- **Download the AOI** in two formats for your internal use:
  - **AOI Summary (JSON)** — total km² with tier and province breakdown, for pricing
  - **AOI Cells (GeoJSON)** — the exact H3 hex polygons, for archive inventory lookup

### Priority tiers

| Tier | Description | Approx. area |
|---|---|--:|
| **P1 — Urban built-up** | Built-up zones around Vietnam's cities and towns | ~15,355 km² |
| **P2 — Road corridors** | 10 km buffer along national roads (motorway, trunk, primary) | ~5,662 km² |
| **P3 — Maritime territories** | Strategic island territories (Trường Sa, Hoàng Sa archipelagos) | ~867 km² |
| **Total initial envelope** | Union of P1–P3 (overlaps removed) | **~20,350 km²** |

Geographic scope: Socialist Republic of Vietnam including recognised maritime territories. CRS: WGS84 (EPSG:4326).

*Note: Vietnam's monsoon season (May–October north; October–January south) produces heavy cloud cover simultaneously across much of the country. We expect multi-date mosaics; re-acquisition policy for cloud-rejected scenes is therefore a key evaluation criterion.*

---

## Image Specifications

| Parameter | Requirement | Notes |
|---|---|---|
| **Ground Sample Distance (GSD)** | ≤ 0.5 m | Sub-metre preferred |
| **Spectral bands** | RGB minimum; multispectral preferred | NIR useful for built-up separation |
| **Cloud cover** | ≤ 30% per scene (≤ 15% preferred) | Cloud-free for island acquisitions |
| **Off-nadir angle** | ≤ 25° preferred | Higher angles accepted for islands only |
| **Geometric accuracy** | CE90 ≤ 5 m absolute | Sufficient for OSM overlay |
| **Acquisition age** | ≤ 18 months from delivery | Fresher preferred for P1 urban |
| **Revisit / update** | Minimum 1× per year per AOI | Quarterly preferred for urban zones |

---

## Delivery Requirements

| Parameter | Requirement |
|---|---|
| **Format** | Cloud-Optimized GeoTIFF (COG) |
| **Tiling** | 256 × 256 px or 512 × 512 px; overview levels included |
| **Delivery mechanism** | S3-compatible object storage |
| **Catalog** | STAC-compatible or manifest JSON per delivery batch |
| **Metadata per scene** | Acquisition date, cloud cover %, sensor ID, off-nadir angle |
| **Lead time** | Archive ≤ 5 business days; new tasking ≤ 8 weeks |
| **Cloud QC** | Scenes exceeding cloud cover threshold replaced at no additional charge |

---

## Licensing Requirements

We require:

1. Commercial use in our navigation products
2. Right to create derivative works extracted from the imagery (vector data, map tiles, enriched road attributes)
3. Redistribution of derivative products to end-users (consumers, fleet operators, B2B partners) without mandatory disclosure of the imagery source
4. No mandatory attribution of the imagery provider in our end-user products
5. Sub-licensing rights when supplying derived map data to third parties

---

## What We Ask From You

Please provide the following so we can complete our evaluation:

1. **Capability statement** — sensor fleet or aggregated sources, GSD range, revisit frequency over Vietnam, archive depth
2. **Archive inventory** — before committing to new tasking, please check the downloadable AOI GeoJSON against your archive at ≤ 0.5 m GSD and ≤ 18 months age and report coverage percentage by tier
3. **Pricing proposal** — using the downloadable AOI Summary JSON as the basis:
   - Archive vs. new tasking price per km²
   - Re-acquisition cost if a scene is cloud-rejected
   - Minimum order and volume tiers
   - Long-term partnership or subscription pricing if available
4. **Sample imagery** — one urban sample (~50 km², suggest central Hanoi or Ho Chi Minh City) and one road corridor sample (~100 km of QL1 central Vietnam) for pipeline evaluation before contract
5. **Delivery timeline** — lead time for the initial envelope; guaranteed % of AOI delivered cloud-free; re-acquisition SLA

---

## Contact

**Lê Quang Tuệ** — Data & Partnerships, TASCO Mapping Division
tuelq@vtii.vn

*This brief is confidential and intended solely for the recipient organisation.*
