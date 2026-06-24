# Work-Done & Plan Report — MapOps Data (O3)

**Reporter:** Tuệ (Geospatial Data Analyst)
**Date:** 2026-06-19
**References:** [OKR 2026.06](./vision/okr-2026.06.md) (O3) · [Enterprise Architecture](./vision/enterprise-architecture.md) · [orchestrator](./README.md)

> Ownership: **O3KR1** (traffic data + admin/POI, with Quân) and **O3KR2** (input pipelines → Editor Spatial DB, solo). This report is structured **KR-by-KR against O3**, then lists the supporting work underneath.

---

## 1 · OKR alignment (the part that matters most)

Status key: **✅ Done** · **🟡 In progress / partial** · **⬜ Not started**

### O3KR1 — Data Editing, Processing & Operations *(Tuệ + Quân)*

| KR | Item | St. | Evidence / notes |
|----|------|-----|------------------|
| 1.1 | Speed limits (HN, HCM, motorway/national highway) | 🟡 | Baseline measured: VN tertiary+ ≈ **133,771 km, 12.9% carry maxspeed** (`traffic/maxspeed/baseline/`). Road-by-road tally `route_coverage.py`. Live edit tool (`app_inspect.py`) + lane visualizer ready. **Remaining: run the evidence-backed hand-edit loop → SOP → editors.** |
| 1.1 | Traffic signals | ⬜ | Deferred since the 06-15 pivot. Needs an in/out decision for T06. |
| 1.1 | Prohibition signs (turn/U-turn/stop/park/**no-overtaking**/one-way) | 🟡 | Pipeline currently pulls only the **speed-limit** family; no-overtaking + the other 5 classes not added yet. |
| 1.2 | Admin boundaries: province → ward → residential area | 🟡 | Geocode dataset (`admin-poi/geocode/`) reaches **ward level** (3,321 wards, 34 provinces, current + 2025 merger). **Residential / sub-ward not yet.** |
| 1.2 | Road hierarchy: street → ngõ → ngách → hẻm (alley levels) | ⬜ | Not started. |
| 1.2 | POI / place data | 🟡 | Coverage planner (`admin-poi/coverage/`): H3 + Open Buildings + OSM, buy-envelope ≈ **20,350 km²**; `cells.parquet` carries `building_count`/`built_up_area_m2`. AWS reverse-geocode crawl method scoped (~$12,762 VN-wide). **Crawl not run yet.** |
| 1.3 | Contributor program (MyTasco) | ⬜ | [T07], not yet due. |

### O3KR2 — Input-data processing application *(Tuệ solo)*

| KR | Item | St. | Evidence / notes |
|----|------|-----|------------------|
| 2.1 | Sign pipeline — **Mapillary** branch | 🟡 | `traffic/signs/mapillary_signs.py` emits the **exact KR2 schema** `[lat,lng,value,object_value,sign_id,first_seen,last_seen]`. Speed-limit family only; writes **parquet**, not the DB. |
| 2.1 | Sign pipeline — **GSV (Google SV)** branch | ⬜ | Paid; **needs budget approval** before building. |
| 2.2 | Process [OSM] → [Editor Spatial DB Server] | ⬜ | Everything is file/parquet today. **Editor Spatial DB = Temporal Spatial DB (Postgres+PostGIS)** not stood up — this is the shared contract with O3KR3 (Quân). |
| 2.3 | Historical traffic-density processing | ⬜ | [T07], not yet due. |

**OKR summary:** the maxspeed core (O3KR1.1) and the Mapillary pipeline (O3KR2.1) already have tooling and base data; the remaining blockers are all either **operational (the edit SOP) or management decisions** (signals in/out, GSV budget, Editor Spatial DB schema) — see §3.

---

## 2 · Supporting work (outside direct KRs)

- **Legal layer** — Circular 38/2024 → OSM tag wiki + speed-limit decision matrix (`wiki/`), **published to Confluence**. Input to the maxspeed decision tree (O3KR1.1).
- **Lane visualizer** (`traffic/lanes/`, SvelteKit) — scores per-road completeness, diffs OSM-vs-Wikidata km, links Mapillary/JOSM/iD evidence; road-by-road QA tool (supports O3KR1.1 and Quân's O3KR3).
- **scite-verified bibliography** (`research/`, 22 papers) — keystone RoadTagger (He et al., 2020) for the "AI detects, rules/graph reason" principle.
- **Dashboards** (`dashboards/`, `traffic/maxspeed/dashboard/`) — cell-map cost estimator + route inspector; basis for budget estimates & progress tracking.
- **Knowledge base / reorg** — repo reorganized to domains-at-root; all strategy/OKR/EA transcribed into `docs/vision/` ([okr-2026.06.md](./vision/okr-2026.06.md) + [enterprise-architecture.md](./vision/enterprise-architecture.md)) + memory.

---

## 3 · Plan (Now → T06)

1. **Run the maxspeed SOP loop (O3KR1.1):** Tuệ + Quân hand-edit one national highway with street-view evidence, screen-record, measure time/km → lock the part-timer budget. Tooling is ready.
2. **Extend the sign pipeline (O3KR2.1):** add the **residential-area + no-overtaking** families to `mapillary_signs.py`; emit **DB rows** instead of parquet.
3. **Ship the building→POI-resolution dashboard (O3KR1.2):** thin Streamlit view over `cells.parquet` → hand H3 cell counts to Vũ for the Amazon cost estimate (task V-4).
4. **Sub-ward + alley levels (O3KR1.2):** extend geocode depth; finalize the 2025 merger dataset.

**Awaiting decisions (these unblock the rest):**

| # | Decision | Blocked KR |
|---|----------|-----------|
| 1 | **Traffic signals** in/out for T06 | O3KR1.1 |
| 2 | **GSV branch budget** | O3KR2.1 |
| 3 | **Lock the Editor Spatial DB schema** (Postgres+PostGIS) with Quân/O4 | O3KR2.2 ↔ O3KR3 |

**Open questions (from the 06-05 minutes):** TomTom free tier @ 15K users · filtering motorbike vs car GPS (Mapillary) · POI one-off vs monthly lease (Mr. Tấn) · final 2025 merger dataset · where to host code with the backend.
