# Unified MapOps Toolkit — execution plan

> Companion to `editor-platform.html` (the intro + how-to one-pager). That page explains *what*
> the system is; this is the *how/when/who* — the plan to turn two separate tools into one toolkit.
> Source of truth lives here; publish to Confluence (NR) via `scripts/confluence_publish.py`.

## 1. Goal

Merge the two editing surfaces the team already built — **RouteSense** (geometry & QA, Quân) and the
**metadata editor** (`traffic/lanes/`, Tuệ) — into **one MapOps Toolkit**: two tracks, one shared
store, one review→approve gate, one push path. Today both are strong but disconnected, and **neither
can write back anywhere** — every edit is hand-applied in iD/JOSM. The plan's job is to close that gap.

## 2. Where we are (verified, Jun 2026)

| Piece | Owner | Status |
|---|---|---|
| RouteSense — C1–C7 route QA + OSMCha-style changeset review, deployed | Quân | ✅ shipped (`crimsonv99.github.io/roadmeter`) |
| Metadata editor — per-way table, maxspeed presets, evidence links | Tuệ | ✅ built (`traffic/lanes/`) |
| QL51 maxspeed pilot — 156 km, 0→100%, ~8 h ≈ 19.5 km/h | Quân (+Tuệ) | ✅ done; SOP + budget left |
| Editor Spatial DB (PostGIS) + write-back | Tuệ ↔ Quân ↔ O4 | 🔲 not started — **the blocker** |

Two redundancies to retire: both tools load a route from **live Overpass** (rate-limited), and both
recompute connectivity + maxspeed coverage. One load, one source of truth per concern.

## 3. Target — the track boundary

One toolkit, two clearly-divided tracks over a shared store. The boundary stops the duplication:

- **Geometry & QA track — Quân (RouteSense).** Road shape/topology (digitise, align, split, conflate),
  connectivity & route-relation integrity (his **C1–C7**), and the **review→approve changeset gate**
  (OSMCha-style diff: tag changes, moved-node arrows, deleted geometry, edit-km by contributor).
  Owns the *verdict* on geometry quality.
- **Metadata track — Tuệ (lanes editor).** Per-way attribute editing driven by **presets** —
  **maxspeed** today, extensible to **lanes / turn / maxheight**. Owns the *values* and their evidence.
- **Shared:** one route-load module, one **Editor DB**, one review gate, one `.osc` push path. The
  metadata editor **consumes** RouteSense's issue list (C1/C3) instead of recomputing it.

POI (AWS reverse-geocode + Open Buildings dedup) and production serving (Martin/Valhalla/OpenSearch)
are **adjacent, not in this plan** — they share the store downstream but aren't editing tracks. Noted
in §7 as dependencies.

## 4. The shared contract — Editor DB schema (the unblock)

The one artifact both tracks must agree on before any write-back exists. Already drafted in
`editor-platform.html`; this plan's first hard milestone is to **lock it**:

`feature` (editable entity: geom + tags jsonb, version/base_version/status) · `observation`
(the OKR row `[lat,lon,loại,giá trị,nguồn,ngày]`) · `suggestion` (posterior + method) · `changeset`
(open→review→approved→pushed) · `edit` (temporal log: before/after, decision, evidence) ·
`preset` (column defs per attribute).

It is the contract between **O3KR2.2** (Tuệ, OSM→Editor DB) and **O3KR3.2** (Quân, write-back/approve).
Until it's signed off with O4, both KRs are blocked.

## 5. Plan — phased, with checkpoints

**Phase 0 — cut the Overpass dependency (now).** *Owner: Tuệ.* Bake `route_geom.py` output → static
JSON per route; Toolkit reads local-first, Overpass fallback only for ad-hoc roads. → *verify: a
frozen-worklist route loads with zero Overpass calls.*

**Phase 1 — converge the front-ends.** *Owners: Tuệ + Quân.* Define one route-load module; RouteSense
exports C1–C7 issues as JSON, the metadata editor displays them inline (no recompute). Tune the
divided-highway false positives (41/48 QL51 flags were separated carriageways read as reversed-oneway).
→ *verify: editing a route in the Toolkit shows Quân's connectivity/maxspeed flags without a second query.*

**Phase 2 — lock the Editor DB schema.** *Owners: Tuệ + Quân + O4.* Ratify §4 DDL, commit it to the
repo as the shared contract. → *verify: schema merged; both KR2.2 and KR3.2 reference the same file.*

**Phase 3 — stand up the Editor DB + import.** *Owner: O4 / Cao Nguyên (backend), Tuệ (import).* PostGIS
on FPT Cloud; import a route from local PBF, recording `base_version` from live OSM. → *verify: one
route round-trips PBF → Editor DB → `.osc` export.*

**Phase 4 — write-back path.** *Owners: Quân (gate) + Tuệ (stage).* Staged edits → `changeset` →
RouteSense review/approve → `.osc` → push to live OSM (+ serve). → *verify: one approved changeset
reaches OSM with evidence attached, fully audited in the `edit` log.*

**Phase 5 — suggestion engine.** *Owner: Tuệ (+ AI later).* Multi-source `observation` rows
(OSM/Mapillary/GSV/satellite/TT38/probe) fused by decision tree (Circular 38 morphology→speed) +
Bayesian posterior → editor accept/override/reject with mandatory street-view evidence.
→ *verify: a suggested maxspeed appears with its sources and posterior; accepting it writes an `edit`.*

**Phase 6 — one web app (decision, not build yet).** JOSM now for geometry; decide whether to clone
**GeoLibre** so both tracks live in one browser app.

**Parallel — SOP & budget (editors).** *Owners: Quân + Tuệ.* Write the QL51 SOP; **measure the urban
(HN/HCM) edit rate separately** before extrapolating ~19.5 km/h across ~28,000 km; use RouteSense's
per-contributor edit-km as the productivity metric for Duy/Việt/Phương.

## 6. OKR linkage

O3KR1.1 (maxspeed pilot) ✅ · O3KR3.3 (QA toolset) ✅ · O3KR2.2 (OSM→Editor DB) → Phases 2–3 ·
O3KR3.1/3.2 (auth + write-back/approve) → Phases 2–4 · KR2a (changeset review) ⚡ done in RouteSense,
folds in at Phase 1.

## 7. Decisions to lock (leadership / cross-team)

1. **Adopt the two-track tool as the official O3 MapOps editor** — not two personal tools.
2. **Lock the Editor DB schema with O4** (§4) — blocks every write-back path; Phase 2 can't start without it.
3. **JOSM vs clone GeoLibre** for in-browser geometry (Phase 6).
4. **GSV budget** + whether Huy's nav-app GPS crawl feeds the same `observation` table (Phase 5).
5. **Editor budget basis:** approve sizing only after the *urban* rate is measured, not the QL51 highway rate.

## 8. Dependencies / out of scope

- **Backend (Editor DB on FPT Cloud)** — O4 / Cao Nguyên; Phases 3–4 depend on it.
- **POI pipeline** — sibling, lands in the same store downstream; tracked under O3KR1, not here.
- **Production serving** (Martin / Valhalla / OpenSearch) — owned by O4; consumes the push path.
