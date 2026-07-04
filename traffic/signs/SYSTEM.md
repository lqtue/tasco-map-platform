# Multi-source maxspeed fusion — system overview & progress

**Audience:** science / data colleagues. **Purpose:** explain what we are building and
report current progress. **Status date:** 2026-06-26. For how to run the code, see
[`README.md`](README.md); this document is the *why* and the *where we are*.

---

## 1. Problem

Vietnam's road network is largely missing speed-limit data: of ~133,771 km of tertiary-and-above
roads in OSM, only **~12.9 %** carry a `maxspeed` tag, and where a tag exists it may be wrong or
stale. We need to build **our own maxspeed dataset** — and, critically, do it with **verifiable
evidence per value**, because bulk-copying speeds from reference layers without evidence gets OSM
changesets reverted and accounts banned.

No single source solves this. The current OSM tag is incomplete and ages. Mapillary's own sign
detector is European-trained and partial over VN. Street-view imagery is plentiful but only gives
us *bearings* to signs, not positions. The legal speed rules (Thông tư 38/2024) give defaults but
not posted exceptions. Waze and other apps have speeds but are lookup-only and unverifiable.

## 2. Core idea

> Treat every data source as a **noisy sensor** measuring one hidden truth — the real maxspeed of
> a road segment — and **fuse** them into a single value **with a calibrated confidence**.

This follows the established crowdsourced-geolocation paradigm (Krylov et al., 2018) and the
*"AI detects, rules/graph reason"* architecture (RoadTagger; He et al., 2020): perception only
produces observations; geometry and probabilistic rules produce the answer. Confidence is not
decoration — it routes the work: high-confidence values auto-fill the dataset, low-confidence ones
go to human editors with the evidence pre-attached.

## 3. Architecture

Everything meets at **one contract — an `observation` row** — so sources never couple to each
other; each is just an adapter producing rows of:

```
geom · attr=maxspeed · value · source · confidence · observed_at · evidence
```

```
 OSM current tag ┐
 Thông tư 38 law ┤ (prior)
 Mapillary signs ┤
 OUR signs       ┼─► observation lake ─► Bayesian fusion ─► prediction + confidence ─► editor ─► applied
 Waze / apps     ┤    (parquet now,      (per segment)      (the "suggestion")        (human +   edit
 GSV / dashcam   ┘     PostGIS later)                                                  evidence)
```

Storage is parquet + DuckDB-spatial today, with column names mirroring the planned PostGIS
`observation`/`suggestion` tables so migration is a straight copy.

## 4. Components (what each does · status)

| Component | Role | Status |
|---|---|---|
| `baseline/` (maxspeed) | OSM current tag + coverage gaps; the worklist & morphology for the prior | ✅ live |
| Thông tư 38 rules (`wiki/`, lanes legal defaults) | the **prior**: legal default speed from road morphology | ✅ rules exist; coarse version wired into the fuser |
| `mapillary_signs.py` | adapter: Mapillary's own pre-detected signs (medium trust) | ✅ live |
| `triangulate.py` | geometry core: multi-view ray intersection → sign position | ✅ built + tested |
| `detections_pull.py` | adapter: pull Mapillary per-image detections → triangulate → score | ✅ built + validated on real data |
| `compare_osm.py` | snap signs to OSM sections; compare values **using edit-time validity** | ✅ built |
| `fuse.py` | the **Bayesian fusion engine** → value + confidence per segment | ✅ drafted + calibrated; pluggable extra sources |
| SAM3 detector | our own perception (replaces Mapillary's detector) | ⏳ planned (next) |
| `observation`/`suggestion` PostGIS tables | the production data substrate | ⏳ designed, not built |
| Editor confidence overlay | surface predictions in the `lanes` editor | ⏳ planned |

## 5. How positions are recovered (triangulation)

A detection in one image gives only a **bearing** from the camera to the sign. We intersect
bearings from several frames that saw the same sign — the rays cross at its ground position:

- `triangulate(origins, dirs)` solves a least-squares ray intersection in a local tangent plane,
  rejecting degenerate near-parallel geometry (the widest pairwise ray angle must exceed 5°).
- `triangulate_ransac(...)` makes it robust to outlier detections and GPS spikes.
- `cluster_signs(...)` dedups repeated detections of one sign with **directional** DBSCAN (position
  + heading + value), so the entering vs leaving sign of a speed zone stay distinct
  (Pedersen & Torp, 2021).

Quality metrics travel with each triangulated sign — `n_views`, `ray_spread_m` (how tightly the
rays cross), `parallax_deg` — and feed its reliability in the fuser.

## 6. The fusion model

For each segment the true maxspeed `V` is a latent categorical variable over allowed speeds. We
compute the full posterior:

```
P(V=v | observations)  ∝  Prior(v)  ·  Π_o  L(obs_o | V=v) ^ w_o
```

- **Prior(v)** — a soft distribution peaked on the **Thông tư 38 legal default** for the segment's
  morphology (class + divided/built-up). Sharp where morphology is known, flat where it isn't.
- **L(obs|v)** — a **distance-aware likelihood**: a posted value supports nearby speeds too
  (sensor/rounding spread, σ≈8 km/h). This is what keeps the posterior from collapsing to a false
  certainty on a single reading.
- **Source reliability** sets each likelihood's sharpness — our multi-view sign (0.85, nudged by
  `n_views`/spread) > Mapillary's detector (0.70) > Waze (0.65) > unknown source (0.60).
- **Weight w_o** — how much the observation counts: **freshness decay** (half-life 6 yr) × a
  **supersession penalty** (×0.25 if a sign image predates the OSM maxspeed). This is the
  temporal-validity insight: a sign is only evidence if it is newer than the value it would correct.
  Crucially, "newer" is measured against **when the `maxspeed` tag value was last *changed*** (read
  from OSM version history), **not** when the way was last touched — a teammate's geometry edit (node
  move, way split) that merely carried an old speed along must not make that speed look fresh. On
  QL.51 this distinction matters: many ways were edited in 2026 for geometry while their maxspeed
  was actually set in 2025 or earlier.
- **Prior strength** — deliberately *weak* (a broad peak): the legal default decides only when
  there is no observation; it must never outvote a single explicit OSM tag or sign.
- **Calibration** — a temperature (T≈1.2) softens naive-Bayes overconfidence so the score is
  usable as a real probability rather than always saturating at 1.0.

**Outputs per segment:** predicted value, **confidence** (posterior of the winner), runner-up +
margin (the uncertainty), and flags for whether the prediction *changes* or *fills* the OSM value.

Adding a source (Waze, MaxBit, a future GSV crawl) is just dropping an observation file and, if
desired, one trust entry — no change to the math.

## 7. Results so far

**Triangulation, real data (Hanoi pilot, 4 tiles):** from Mapillary per-image detections we
recovered sign positions with **median ~3.7 m error** vs Mapillary's own published positions
(p90 ~3.9 m), ray spread ~0.08 m, ~4 views/sign — i.e. the rays cross cleanly and the bearing
geometry is correct. (Below the ~5 m target seen in the literature; note this is the *disagreement*
between two methods, both with GPS noise, not absolute error.)

**Fusion, calibrated behaviour (synthetic self-check):**
- stale OSM 60 vs two fresh multi-view 80-signs → **80 @ 0.80** (signs override the stale tag)
- OSM 90 + a fresh 90-sign agree → **90 @ 0.87** (high-confidence, auto-fill bucket)
- fresh Waze 100 vs fresh sign 80 (conflict) → **90 @ 0.39, margin 0.05** (correctly uncertain; the
  legal prior breaks the tie rather than a coin-flip)
- lone explicit OSM 40 (legal default 90) → **40 @ 0.33** (a single tag is preserved, never
  overridden by the morphology default — the calibration fix this run surfaced)

**Every non-trivial component ships a runnable self-check** (`triangulate.py`,
`detections_pull.py --selfcheck`, `fuse.py --selfcheck`) — all green.

**QL.51 end-to-end (complete):** the named-route run pulled QL.51's OSM geometry (**309 ways,
100 % already maxspeed-tagged**), crawled the corridor (661 Mapillary detections → **574 fresh**
after a 24-month image filter → **123 triangulated signs**, median error **5.4 m** vs Mapillary's
ref, p90 27.4 m — wider than the Hanoi pilot because corridor tiles also catch side-road signs),
and fused against OSM + the legal prior. Findings:

- **Snap to road:** of 123 signs, 50 lie on QL.51 (≤30 m), 73 are off-route side-road signs
  (correctly skipped). Of the on-route ones: 27 **agree** with OSM, 23 **disagree**.
- **All 23 disagreements were flagged `re-verify`, not `fix-OSM`** — because QL.51's OSM `maxspeed`
  was mass-edited in 2026 (Apr–Jun), *newer* than the 2024–25 sign images. The edit-time validity
  gate working exactly as intended: stale evidence cannot silently override a fresh edit.
- **Geometry-edit vs maxspeed-edit (important correction):** QL.51's OSM ways were largely *touched*
  in 2026, but reading the OSM **version history** shows many had their `maxspeed` value actually set
  in **2025 or earlier** — the 2026 edits were geometry. Keying freshness on the maxspeed value's
  last-change date (not the way's last touch) is what lets a 2024–25 sign legitimately challenge a
  speed that only *looks* fresh. (Cached per way in `data/<ref>_msage.json`.)
- **Fusion, signs only:** with the way's last-touch date everything was suppressed (0 changes);
  with the **corrected maxspeed-age**, signs alone yield **5 changes, 4 high-confidence** — the fix
  surfaced real signal that the naïve date was hiding.
- **Fusion + a fresh second source (synthetic Waze layer, for demonstration):** adding fresh
  corroborating observations at the strong sign clusters produced **12 changes, 7 high-confidence**,
  e.g. one way: OSM 90 → **50 @ 0.99** from 9 agreeing observations. The core result — *one stale
  source cannot move an authoritative fresh tag, but a fresh corroborating source tips the same
  evidence into a confident, actionable recommendation.* (The Waze layer is synthetic, so this
  demonstrates the fusion mechanics + the `--extra` plug, not a real QL.51 finding.)

## 8. Limitations & open questions (for discussion)

- **Bearing convention** is validated on spherical (360°) cameras; the perspective/fisheye branch
  is not yet checked on live data — matters for dashcam imagery.
- **Reliability and weight constants are hand-set priors**, not learned. They should be calibrated
  against a ground-truth sample (field survey or hand-labelled segments) — a good science task.
- **Naive-Bayes independence** assumes sources are conditionally independent; correlated sources
  (e.g. Waze and OSM both copied from the same survey) would double-count. Per-source weights only
  crudely mitigate this.
- **Legal prior is coarse** (class + divided heuristic); the full Thông tư 38 decision matrix +
  built-up detection is the upgrade.
- **Mapillary coverage is sparse and uneven** over VN; many segments will have no sign observation
  and fall back to OSM + prior only.
- **Split-inheritance edge case:** a way *created* by a split carries its parent's `maxspeed` at
  version 1, so the history shows the value "set" at the split time (recent) even though it was
  inherited, not re-confirmed. The maxspeed-age fix handles in-place edits correctly but can still
  over-trust a freshly-split way; detecting inheritance needs cross-referencing the parent's history.

## 9. Next steps

1. Finish + report the QL.51 fusion run; add a synthetic Waze layer to demonstrate multi-source.
2. SAM3 detector on our own crawled images (replaces Mapillary's detector; same geometry).
3. Calibrate reliability/weights against a labelled ground-truth sample.
4. Stand up the `observation`/`suggestion` substrate (parquet lake → PostGIS) and a confidence
   overlay in the `lanes` editor.

## References

- He, S., et al. (2020). RoadTagger: robust road attribute inference with GNNs. *AAAI*. https://doi.org/10.1609/aaai.v34i07.6730
- Krylov, V. A., Kenny, E., & Dahyot, R. (2018). Automatic discovery and geotagging of objects from street view imagery. *Remote Sensing*, 10(5), 661. https://doi.org/10.3390/rs10050661
- Krylov, V. A., & Dahyot, R. (2019). Object geolocation from crowdsourced street level imagery. https://doi.org/10.1007/978-3-030-13453-2_7
- Geolocating traffic signs using crowd-sourced imagery (2020). https://doi.org/10.1145/3397536.3422340
- Pedersen & Torp (2021, directional clustering); Newson & Krumm (2009, HMM map-match) — in `archive/research/README.md`.

*Full method bibliography: [`README.md`](README.md) and `archive/research/README.md`.*
