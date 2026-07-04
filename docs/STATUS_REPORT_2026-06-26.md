# Work-Done & Plan Report — Multi-source maxspeed dataset (O3)

**Reporter:** Tuệ (Geospatial Data Analyst)
**Date:** 2026-06-26
**Audience:** science / data colleagues
**References:** [signs system doc](../traffic/signs/SYSTEM.md) (full method) · [prior report 2026-06-18](../archive/docs/STATUS_REPORT_2026-06-18.md) · [OKR 2026.06 O3]

> This period built the **end-to-end pipeline that turns every available source into one maxspeed
> dataset with a calibrated confidence** — the substance behind O3KR2.1 (sign pipeline) and the
> feed into O3KR1.1 (speed limits). It is prototyped and validated on a real national route (QL.51).
> Code: `traffic/signs/`. Deep doc: [`SYSTEM.md`](../traffic/signs/SYSTEM.md).

---

## 1 · TL;DR

- We can now **crawl street-view imagery, detect signs, and recover their real ground position by
  triangulating across frames** — our own positions, not a vendor's. Validated: median **3.7 m**
  (Hanoi pilot) / **5.4 m** (QL.51) vs Mapillary's reference.
- A **Bayesian fusion engine** merges the OSM tag, our triangulated signs, the Thông tư 38 legal
  prior, and any external app (Waze, …) into **one predicted speed + confidence** per road segment.
- A **temporal-validity gate** decides whether each piece of evidence still counts — and a fix this
  period made it read the **OSM edit history** so a teammate's *geometry* edit is not mistaken for a
  fresh *speed* edit. On QL.51 this re-dated **70 % of ways**.
- Every component ships a runnable self-check; all green. Nothing is written to OSM — outputs are
  suggestions for human review with evidence attached.

## 2 · What was built (this period)

| Component (`traffic/signs/`) | What it does | Status |
|---|---|---|
| `triangulate.py` | geometry core: multi-view ray intersection → sign position (RANSAC-robust; directional-clustering dedup) | ✅ built + tested |
| `detections_pull.py` | Mapillary adapter: per-image detections → bearings → triangulate → score vs reference | ✅ validated on real data |
| `compare_osm.py` | snap signs to OSM sections; compare speeds using **edit-time validity** (incl. history-based maxspeed age) | ✅ built |
| `fuse.py` | **Bayesian fusion** → value + confidence per segment; pluggable extra sources (`--extra`) | ✅ drafted + calibrated |
| MapOps Toolkit overlay | Mapillary speed-sign layer in the `lanes` editor (evidence while editing) | ✅ shipped |

The architecture invariant throughout: **AI detects, rules/graph reason** (RoadTagger, He et al.,
2020). Sources only emit observations; geometry + probabilistic rules produce the answer.

## 3 · How the fusion works (one paragraph)

Each source is a noisy sensor of one hidden truth. For each segment we compute
`P(V=v | obs) ∝ Prior(v) · Π L(obs|v)^w`: the **prior** is the Thông tư 38 legal default from
morphology (deliberately weak — it decides only with no evidence); each **observation** contributes
a distance-aware likelihood scaled by **source reliability** (our multi-view sign > Mapillary's
detector > Waze) and a **weight** = freshness decay × a supersession penalty. The **prediction** is
the posterior peak; the **confidence** is its probability (temperature-calibrated so two agreeing
fresh sources read ~0.87, a lone tag ~0.33, a conflict ~0.39). Confidence routes the work:
high-confidence auto-fills, low-confidence goes to a human with the evidence attached.

## 4 · Key results (QL.51, Biên Hòa → Vũng Tàu)

- **Triangulation:** 661 Mapillary detections → 574 fresh → **123 triangulated signs**, median
  **5.4 m** vs reference. 50 lie on QL.51, 73 are correctly-skipped side-road signs.
- **Geometry-edit vs maxspeed-edit (the important finding):** reading OSM version history,
  **217 of 309 ways (70 %)** had their `maxspeed` set *before* their last touch — last-touch dates
  say 275 ways are "2026-fresh", but the speed was actually set then on only **86**; the rest trace
  back through 2025 (186) to as old as 2013. The naïve "last edit" gate was over-trusting ~189 ways.
- **Fusion, signs only:** with the corrected maxspeed-age, signs alone yield **5 changes,
  4 high-confidence** (the naïve date had suppressed all of them).
- **Fusion + a fresh corroborating source (synthetic Waze, for demo):** **12 changes,
  7 high-confidence**, e.g. one way OSM 90 → **50 @ 0.99** from 9 agreeing observations. The thesis:
  *one stale source can't move an authoritative fresh tag, but a fresh corroborating source tips the
  same evidence into a confident, actionable recommendation.*
- **Honest note on QL.51:** OSM is already 100 % maxspeed-tagged and partly freshly edited, so for
  this road the exercise is mostly *confirmation*, not enrichment. The system's value is largest
  where OSM is missing or genuinely stale — and where imagery is fresher/denser than QL.51's.

## 5 · O3 OKR alignment

| KR | Item | St. | This period |
|----|------|-----|-------------|
| 2.1 | Sign pipeline — Mapillary | 🟡→🟢 | Beyond re-serving vendor points: we now **detect-position our own signs** (triangulation) and **fuse** them. Speed-limit family; parquet (schema mirrors the planned PostGIS `observation` table). |
| 2.2 | OSM → Editor Spatial DB | ⬜ | Observation/suggestion **schema exercised in parquet**; ready to lift into PostGIS once the schema is locked with Quân/O4. |
| 1.1 | Speed limits | 🟡 | The fusion engine **produces the editor worklist** (high-confidence changes + missing fills), each with evidence — the input to the hand-edit SOP. |

## 6 · Limitations & open questions (for the science team)

- **Reliability/weight constants are hand-set priors, not learned.** They should be **calibrated
  against a ground-truth sample** (field survey or hand-labelled segments) — a clean science task.
- **Naive-Bayes independence** double-counts correlated sources (e.g. Waze copied from OSM); only
  crudely mitigated by per-source weights.
- **Bearing convention** is validated on 360° (spherical) cameras; the perspective/fisheye branch
  is untested on live data (matters for dashcam).
- **Split-inheritance edge:** a way *created* by a split inherits maxspeed at version 1, so history
  shows it "set" at split time even if not re-confirmed; needs parent-history cross-reference.
- **Legal prior is coarse** (class + divided); upgrade = full Thông tư 38 matrix + built-up detection.
- **Mapillary coverage is sparse/uneven** over VN; many segments fall back to OSM + prior only.

## 7 · Next steps

1. **SAM3 detector** on our own crawled images (replaces Mapillary's detector; same geometry) — the
   path to VN-accurate recall and classes beyond speed limits.
2. **Calibrate** reliability/weights against a labelled ground-truth sample.
3. **Stand up the observation/suggestion substrate** (parquet → PostGIS) and a **confidence overlay**
   in the `lanes` editor, so editors work the ranked, evidence-backed queue directly.
4. Run on a road where OSM is **missing/stale** (not QL.51) to show enrichment, not just confirmation.

## References

- He et al. (2020). RoadTagger. *AAAI*. https://doi.org/10.1609/aaai.v34i07.6730
- Krylov, Kenny & Dahyot (2018). Automatic discovery and geotagging of objects from street view imagery. *Remote Sensing*, 10(5), 661. https://doi.org/10.3390/rs10050661
- Full method + bibliography: [`traffic/signs/SYSTEM.md`](../traffic/signs/SYSTEM.md), [`traffic/signs/README.md`](../traffic/signs/README.md), `archive/research/README.md`.
