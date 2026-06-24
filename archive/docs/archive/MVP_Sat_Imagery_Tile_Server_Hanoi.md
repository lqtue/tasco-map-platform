# Satellite Imagery Timeseries Tile Server — MVP Plan

**Project:** TASCO Map Platform — First Assignment  
**Scope:** Timeseries XYZ tile server for a region in Hanoi  
**Goal:** Give MapOps editors satellite basemap imagery at multiple dates so they can digitize and verify road features in JOSM/iD

---

## 1. Area of Interest

**Hanoi urban core + western expansion corridor**  
Bounding box: approximately `20.95°N – 21.10°N`, `105.75°E – 105.90°E`

This covers the Old Quarter, Cầu Giấy, Thanh Xuân, Nam Từ Liêm, and the Nhổn–Hà Nội metro corridor — areas with active construction, new road geometry, and high TASCO priority for OSM data quality. Roughly 20 × 15 km.

Why this AOI: dense enough that MapOps will immediately use the imagery for editing, dynamic enough that timeseries comparison reveals road changes, small enough to keep storage and compute costs trivial for the MVP.

---

## 2. The Imagery Source Problem

This is the hardest decision in the project. Each source has a resolution / cost / freshness / licensing tradeoff:

| Source | Resolution | Useful to zoom | Revisit | Practical freshness | Cost | OSM editing usable? | Licensing |
|--------|-----------|----------------|---------|---------------------|------|---------------------|-----------|
| **HLS (Landsat+S2 harmonized)** | 30m | z12 | ~2–3 days combined | Multiple per week (clouds permitting) | Free | No — change detection only | Open (NASA) |
| **Sentinel-2 L2A** | 10m | z14 | 5 days (S2A+S2B) | One usable scene every 2–4 weeks in monsoon | Free | No — too coarse for road geometry | Open (Copernicus) |
| **NICFI/Planet archive** | 4.77m | z15 | Monthly | Frozen — program ended Jan 2025 | Was free | Marginal | Non-commercial only |
| **Planet PlanetScope** | 3–5m | z15–16 | **Daily** | Fresh most clear-sky days | Commercial (~$5–15/km²/yr) | Marginal | Commercial |
| **Airbus (Pléiades / SPOT)** | 0.5–1.5m | z18 | Tasking on demand | 1–7 day tasking lag; archive varies | Expensive | Yes | Commercial |
| **Maxar (WorldView)** | 0.3–0.5m | z19 | Tasking on demand | 1–7 day tasking lag; archive varies | Expensive (~$15–25/km²) | Yes — street-level detail | Commercial |
| **Drone (in-house)** | 2–10cm | z20+ | **You choose** | Same day | One-time flight | Yes — sharpest of all | Owned |
| **Bing Maps Aerial** | 0.3–1m | z18–19 | Mosaic refresh irregular | **Months to years stale** | Free for OSM editing | Yes — already in JOSM | Microsoft ToS |
| **Esri World Imagery** | 0.3–1m | z18–19 | Mosaic refresh irregular | Patchwork of dates within one tile | Free for display | Yes — but no timeseries | Esri ToS (display only) |
| **Google Earth tiles** | 0.3–1m | z18–19 | Mosaic refresh irregular | Historical slider in GE Pro | Not legally reusable | Yes visually | Not redistributable |

**Key insight from the table:** the free high-res sources (Bing, Esri, Google) look sharp but their "latest" pixel is often **months to years old**, and you cannot legally re-serve them. The free fresh sources (HLS, Sentinel-2) are current but too coarse for road editing. **Nobody serves "free + sub-meter + known-recent"** — that gap is the value this platform creates.

**Source selection (what we ingest into the platform): two phases**

- **Phase 1 — HLS / Sentinel-2 for timeseries proof of concept.** Free, immediate access, COG format already available. 10–30m is too coarse for street-level editing, but it proves the infrastructure: temporal URL scheme, STAC catalog, date picker in the UI. Ships weeks 1–2.
- **Phase 2 — evaluate one commercial source for production editing layer.** Start with **Planet** (Education / trial). If sub-meter is required, evaluate **Maxar** SecureWatch or **Airbus** OneAtlas. Drone flights are the realistic path for sustained sub-meter coverage of priority corridors.

**What NOT to do:** Don't proxy Google / Bing / Esri tiles and re-serve them — ToS violation and legal risk. The MapOps team already has Bing in JOSM natively, so that's a complement, not a competitor (see §2A).

---

## 2A. How editors will actually use this — the two-layer stack

Resolution and freshness are not the same axis, and the platform's role is best understood by separating them. In day-to-day editing the MapOps team will run a **two-layer stack**:

| Layer | Source | Role | When the editor looks at it |
|-------|--------|------|------------------------------|
| **Basemap (always on)** | Bing / Esri (already in JOSM/iD) | High-resolution reference for digitizing road geometry, building outlines | Constantly, at z17–z19 |
| **Timeseries (toggled)** | **This platform** (HLS now → Planet / Maxar / drone later) | Known-recent date(s) for change detection and verification | When the editor asks "*is this still here?*" or "*when did this appear?*" |

So the value proposition is **not** "replace Bing with something sharper." It's "give editors a *dated* view of the same area that Bing shows undated." Concretely:

- **Spot a new road or construction site fast.** Sentinel-2 / HLS at z12–z14 catches new geometry within 2–4 weeks. Bing might catch it in 2 years.
- **Verify a feature is still there.** Scrub the date slider — if a building shows in 2024-03 but not 2024-09, demolition is the story.
- **Resolve "outdated basemap" disputes.** Bing tile says one thing, the editor's local knowledge says another → the dated timeseries is the tie-breaker.

| Editor need | Best free option today | Gap this platform fills |
|---|---|---|
| See a road at z18 | Bing (but dated unknown) | Add a *known-recent* layer alongside |
| See a road *change over time* | Nothing free | The whole point of the timeseries |
| Spot a *new* construction site fast | None below ~1 year stale | Monthly HLS/S2 composite catches it within ~30 days |

This framing also clarifies the resolution debate: the timeseries layer **does not need to match Bing's resolution to be valuable**. It needs to be (a) recent, (b) of *known* date, and (c) consistent month-over-month. HLS at 30m satisfies all three for change detection. Commercial sub-meter is the upgrade path for *editing on the timeseries layer itself*, which is a later, narrower use case (priority corridors, drone-supplemented).

---

## 3. Technical Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                         │
│  JOSM / iD editor / QGIS / Internal web viewer          │
│  XYZ URL: https://tiles.internal/{date}/{z}/{x}/{y}.png │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│                   SERVING LAYER                          │
│  Nginx reverse proxy (caching, auth, rate limiting)      │
│  ↓                                                       │
│  TiTiler (FastAPI) — dynamic tile rendering from COGs    │
│  Reads COGs directly from S3 via HTTP range requests     │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│                   STORAGE LAYER                          │
│  S3 bucket: s3://tasco-imagery-hanoi/                    │
│  ├── sentinel2/                                          │
│  │   ├── 2024-01/composite.tif  (COG)                    │
│  │   ├── 2024-02/composite.tif  (COG)                    │
│  │   └── ...                                             │
│  └── planet/     (when acquired)                         │
│      ├── 2024-01/mosaic.tif     (COG)                    │
│      └── ...                                             │
│                                                          │
│  STAC catalog: stac-catalog.json                         │
│  (one Item per temporal snapshot, links to COG assets)    │
└──────────────────────────────────────────────────────────┘
```

**Key design decisions:**

**TiTiler over pre-rendered tiles.** For an MVP with a small AOI and <20 concurrent users (the internal map team), TiTiler dynamically rendering tiles from COGs on S3 is simpler and cheaper than pre-generating PMTiles archives. If performance becomes an issue at scale, migrate to PMTiles later — the COGs on S3 are the same source data either way.

**Temporal URL scheme.** The URL `/{date}/{z}/{x}/{y}.png` maps to a TiTiler request that looks up the correct COG for that date from the STAC catalog. For the MVP, `{date}` is `YYYY-MM` (monthly granularity for Sentinel-2 composites). A `/latest/{z}/{x}/{y}.png` alias always serves the most recent snapshot.

**STAC catalog.** Even for the MVP, use STAC from day one. It's a flat JSON file at this scale (no need for pgSTAC or STAC API server). Each Item has a datetime, bbox, and link to the COG on S3. When the team adds Planet or Maxar imagery later, it slots into the same catalog structure.

---

## 4. Implementation Plan

### Phase 1: Infrastructure (Week 1)

- [ ] Provision S3 bucket (`tasco-imagery-hanoi`) in `ap-southeast-1`
- [ ] Deploy TiTiler on the existing Vultr VPS (Docker container, port 8080)
- [ ] Configure Nginx reverse proxy: TLS, basic auth, tile caching (1-hour TTL for MVP)
- [ ] Verify end-to-end: upload a test COG to S3, confirm XYZ tiles render in browser

**Done when:** a hand-uploaded test COG renders as XYZ tiles in a browser via the public `https://tiles.tasco-internal.vn` URL.

### Phase 2: Sentinel-2 Timeseries Pipeline (Week 2)

- [ ] Write Python script to query Element 84 Earth Search STAC API for Sentinel-2 L2A scenes covering the Hanoi AOI
- [ ] For each month (Jan 2023 → present): find least-cloudy scene, download B04/B03/B02 (RGB) bands
- [ ] Composite into a single true-color COG per month using `rasterio` + `rio-cogeo`
- [ ] Clip to AOI bounding box, reproject to EPSG:3857 (Web Mercator)
- [ ] Upload COGs to S3, generate STAC catalog JSON
- [ ] Build the temporal routing layer in TiTiler (FastAPI middleware that resolves `/{date}/` to the correct COG)
- [ ] Test in JOSM: add as custom TMS layer, verify tile loading at zoom 10–15

**Done when:** in JOSM, switching the date in the TMS URL between two ingested months shows visibly different imagery over Hanoi at z12–z14.

### Phase 3: Validation & Editor Integration (Week 3)

- [ ] Write TMS endpoint config for JOSM (XML imagery entry) and share with MapOps engineer
- [ ] Document: how to add the layer in JOSM, how to add the layer in iD, available dates
- [ ] Test with MapOps engineer: is the imagery usable for their editing workflow? What's missing?
- [ ] *(Optional, QA only — not blocking)* Build a minimal web viewer (Leaflet or MapLibre GL JS) with a date slider for demos / non-editor stakeholders.

**Done when:** the MapOps engineer, working in their normal JOSM setup, can toggle the TASCO layer over their Bing basemap and articulate at least one concrete use (change detection / verification / dispute resolution — per §2A) where the layer answered a real editing question.

---

## 4A. Post-MVP work

These were originally listed as "Phase 4, parallel" but have been pulled out of the MVP so the team isn't running two workstreams before Phase 1–3 ship. They start *after* the MVP done-when checks pass.

**Commercial imagery evaluation** (begins after Phase 3 sign-off):

- [ ] Apply for Planet trial / education access for the Hanoi AOI
- [ ] If approved: download PlanetScope scenes for 3–5 dates, convert to COG, add to the same pipeline as a new `planet` source
- [ ] Compare: can the MapOps engineer digitize road features at Planet's 3–5 m resolution?
- [ ] If not sufficient: prepare a cost estimate for Maxar / Airbus sub-meter imagery and present to team lead
- [ ] Document findings in a source evaluation report (feeds into the Geospatial Data Analyst role's data source registry)

**Done when:** a written recommendation exists for the next imagery tier (Planet vs Maxar vs Airbus vs drone) with cost, freshness, and resolution numbers grounded in actual sample imagery over Hanoi — not vendor brochures.

---

## 5. Cost Estimate (MVP)

| Item | Cost | Notes |
|------|------|-------|
| Sentinel-2 imagery | $0 | Copernicus open data |
| S3 storage (est. 50 GB for 18 months of monthly COGs) | ~$1.15/month | S3 Standard, ap-southeast-1 |
| S3 egress (est. 50 GB/month internal use) | ~$4.50/month | To VPS for tile rendering |
| TiTiler on Vultr VPS | $0 incremental | Runs on existing vc2-2c-4gb alongside Cantaloupe |
| Planet trial imagery | $0 (if approved) | Education/trial program |
| **Total MVP monthly cost** | **~$6/month** | Excludes commercial imagery procurement |

---

## 6. What the MVP Proves

**For the team:** editors keep Bing as their always-on high-res basemap and toggle the TASCO timeseries layer when they need a *dated* view — to detect new roads, verify a feature is still there, or settle "is the basemap outdated?" disputes. The platform's role is complementary to Bing, not a replacement (see §2A).

**For the architecture:** the COG + S3 + TiTiler + STAC stack works, temporal routing works, and new imagery sources (Planet, Maxar, drone) slot in by dropping COGs in the bucket and appending STAC items — no architectural changes needed. Resolution scales **up** through the same pipes as budget allows.

**For your role:** this is the bridge deliverable. It proves you can ship infrastructure (the tile server), while the source evaluation and cost analysis work (§4A Post-MVP) is the beginning of the data acquisition function that differentiates your role from the other MapOps engineer.

---

## 7. Known Limitations & Next Steps After MVP

**Resolution gap is by design, not a flaw.** Under the two-layer framing (§2A), Bing remains the high-res basemap and the TASCO layer is the dated overlay — so 10–30m HLS/Sentinel-2 is sufficient for change detection from day one. Commercial sub-meter and drone are upgrades for *editing on the timeseries layer itself* over priority corridors, which is a later, narrower scope.

**Cloud masking.** The MVP uses "least cloudy scene per month" which is crude. A production pipeline would need proper cloud masking (using Sentinel-2 SCL band) and multi-scene compositing.

**Scaling.** TiTiler on a single VPS handles the 5-person founding team. If T-Maps goes to production and external users need imagery, this needs to move to AWS (Lambda + API Gateway + CloudFront) or pre-rendered PMTiles on S3.

**Additional data types.** Once the pipeline works for satellite imagery, the same architecture serves aerial photography, drone imagery, and dashcam-derived orthomosaics — all as COGs in S3 with STAC metadata.

---

## 8. Key Dependencies

| Dependency | Owner | Status |
|-----------|-------|--------|
| Vultr VPS access | You | Existing (Cantaloupe already running) |
| AWS account with S3 access | Team lead / DevOps | Needs provisioning |
| JOSM/iD configured for internal TMS | MapOps engineer #1 | After Phase 2 |
| Planet trial application | You | Apply Week 1 |
| Budget approval for commercial imagery (if needed) | Team lead | After Phase 4 evaluation |
