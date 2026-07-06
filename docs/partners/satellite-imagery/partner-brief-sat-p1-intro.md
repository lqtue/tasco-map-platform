# Introduction — TASCO Mapping Division
**TASCO Mapping Division** · 2026-06 · Confidential

---

Dear Partner,

We are reaching out to explore a data partnership with your organisation. This letter introduces who we are and what we are building. A follow-up brief with our specific technical requirements and area-of-interest data will be shared separately.

## About TASCO

**TASCO Mapping Division** is the geospatial data and navigation arm of **TASCO Group**, Vietnam's leading transportation conglomerate with approximately 10,000 employees and operations spanning toll infrastructure, transit, and mobility services.

Through **VETC**, TASCO operates **75% of Vietnam's Electronic Toll Collection (ETC) network** — 4.2 million registered vehicle owners and over 2 million toll transactions processed daily across the national highway system.

TASCO's technology subsidiary, **VTII**, develops and operates the platform stack that the Mapping Division's data feeds.

## What We Are Building

We are building **Vietnam's first self-owned, daily-fresh, legally clean national map platform** — purpose-built for real-time driver assistance, logistics, and ADAS.

**Core products:**
- **V-Base-Maps** — a daily-updated national road graph (OpenStreetMap and Overture Maps as base) enriched with AI-detected attributes: speed limits, lane counts, traffic signs, and road morphology
- **V-Navigation-Maps** — turn-by-turn routing with *just-in-time* lane-level alerts (speed limit warnings, lane-change guidance, enforcement camera positions) delivered *before* the driver needs to act

Our platform feeds our consumer navigation app (MyTasco), VETC fleet management, and B2B logistics and automotive partners.

**Why we build rather than buy:** existing commercial map providers either prohibit use on competing surfaces, carry stale road geometries (2–3 years behind), or lack the attribute depth needed for lane-level guidance. Building on open base data gives us a legally clean, self-owned foundation with full control over enrichment and updates.

## Why We Need Satellite Imagery

Our speed-limit enrichment pipeline assigns legal default speeds from Vietnamese traffic law (Thông tư 38/2024/TT-BGTVT), but those defaults depend on whether a road segment runs through a *built-up area*. OSM currently classifies fewer than 30% of Vietnam's road network with sufficient morphology tags to derive this automatically.

Satellite imagery fills four gaps we cannot resolve from any other source:

1. **Urban boundary detection** — identify built-up extents to assign the correct legal speed default across 116,498 km of road currently missing a maxspeed tag
2. **AI geometry extraction** — segmentation of road surfaces, building footprints, and natural features to auto-generate and validate road geometry in provinces with sparse community editing
3. **Road network verification** — detect missing segments, misaligned geometries, and construction-stage roads before they enter the routing graph
4. **Maritime territory coverage** — Vietnam's strategic island territories have zero street-view accessibility; satellite is the only viable source for road and infrastructure mapping there

## Partnership Interest

We are in active evaluation of satellite imagery providers for both an **initial bulk acquisition** and an **ongoing annual update** arrangement. We are open to discussing long-term partnership structures as well as standard commercial procurement depending on the provider's preferred model.

We would welcome the opportunity to learn more about your capabilities and to share our technical requirements in detail.

---

**Next step:** if this introduction is of interest, we will follow up with our technical requirements brief and interactive area-of-interest data (including a downloadable AOI file for your archive inventory check).

**Contact:**
Lê Quang Tuệ — Data & Partnerships, TASCO Mapping Division
tuelq@vtii.vn

*This letter is confidential and intended solely for the recipient organisation.*
