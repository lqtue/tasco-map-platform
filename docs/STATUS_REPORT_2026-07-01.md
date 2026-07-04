# Repo Status Report — `tasco-map-platform`

**Date:** 2026-07-01
**Branch:** `cleanup/reorg-artefacts`
**Reporter:** Tuệ

> Snapshot of repository state. The full O3KR2 sign-fusion deliverable is **built and validated but not yet committed** — see [prior report 2026-06-26](STATUS_REPORT_2026-06-26.md) for the method write-up.

## 1 · Working tree

Last commit (`ae51917`) is docs-only. All substantive work from this cycle is uncommitted.

| | Files | State |
|---|---|---|
| **New — `traffic/signs/` sign pipeline** | `triangulate.py`, `detections_pull.py`, `compare_osm.py`, `fuse.py`, `inspect_map.py` + `README.md`, `SYSTEM.md` | untracked (~1,600 LoC) |
| **New — editor overlay** | `traffic/lanes/src/lib/osm/mapillary.ts` (105) + `MapView.svelte` (+109) | untracked / modified |
| **New — status report** | `docs/STATUS_REPORT_2026-06-26.md` | untracked |
| **Modified docs** | `CLAUDE.md`, `traffic/lanes/CLAUDE.md`, `archive/research/README.md`, `.gitignore` | modified |

**Risk:** the whole O3KR2 sign-fusion deliverable sits outside git.

## 2 · Where the project stands

- **Built + validated this cycle:** street-view → detect → triangulate (own sign positions, median 3.7–5.4 m vs Mapillary) → Bayesian fusion → per-segment speed + confidence. Prototyped on **QL.51**.
- **Key finding:** temporal-validity gate now reads OSM *version history*, not last-touch — fixed a bug where geometry edits masqueraded as fresh speed edits (re-dated 70 % of QL.51 ways).
- **Two live web apps** (unchanged): `traffic/lanes/` (MapOps Toolkit) + `traffic/sat-imagery/`, both on GitHub Pages. Everything else archived.

## 3 · OKR alignment

| KR | Item | Status |
|----|------|--------|
| 2.1 | Sign pipeline — Mapillary | 🟡→🟢 — past re-serving vendor points to own detect + fuse |
| 2.2 | OSM → Editor Spatial DB | ⬜ — schema exercised in parquet, not yet in PostGIS |
| 1.1 | Speed limits | 🟡 — fusion now produces the editor worklist |

## 4 · Open / next

- Detector is still Mapillary's (SAM3 planned).
- Fusion constants are hand-set, not calibrated against ground truth.
- QL.51 is 100 % tagged → *confirmation not enrichment*; needs a run on a stale road.
- **Immediate action:** commit the `traffic/signs/` pipeline.
