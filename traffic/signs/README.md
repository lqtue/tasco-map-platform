# `traffic/signs/` — street-view sign detection → triangulated positions

> **System overview & progress report** (for science/data colleagues — the *why* and *where we
> are*, incl. the Bayesian fusion model and results): [`SYSTEM.md`](SYSTEM.md). This README is the
> developer how-to.

Two tracks live here:

1. **Mapillary re-serve (live):** `mapillary_signs.py` pulls Mapillary's *own* pre-detected
   speed-limit signs over a bbox → `mapillary_sign_points.parquet`. One published point per sign,
   European-trained detector, no control over recall/classes. This is the "phase-1" feed used by
   the dashboards and the `traffic/lanes/` editor overlay.
2. **Self-crawl + triangulate (this design doc):** crawl street-view imagery, run *our* detector
   (SAM3), and recover each sign's real ground position by **triangulating the same sign across
   multiple frames**, then dedup repeated detections into one physical sign. This is the missing
   **denoise + localize (SP3)** link, and the path to VN-accurate, our-own sign positions.

This README is the design doc for track 2 + how to run its first prototype.

## Why triangulate

A single detection tells you only a **bearing** from the camera to the sign — not how far away it
is. Mapillary's published point is one provider's guess. To get a trustworthy position we intersect
bearings from several frames that saw the same sign: the rays cross at the sign. This is the
standard crowdsourced object-geolocation method (Krylov, Kenny & Dahyot, 2018, *Remote Sensing*,
doi:10.3390/rs10050661; and the traffic-sign-specific work, doi:10.1145/3397536.3422340,
doi:10.1145/3469830.3470900). Architecture invariant: **AI detects, geometry/rules reason** — the
detector only emits rays + a value; position comes from geometry, the speed value from the sign
class + Thông tư 38 rules (RoadTagger, He et al., 2020).

## Pipeline (source-agnostic)

```
 imagery source (pluggable)          perception          geometry             store
 ├ Mapillary API (images+pose+det)┐
 ├ Google Street View (later)     ┼─►SAM3 detect+value─►bearing ray────►RANSAC multi-view──►directional
 └ own dashcam + GPS/IMU (later)  ┘  (zero-shot now)    per detection    triangulation       cluster
                                                        (+mono-depth                          (dedup)
                                                         fallback)                              │
                                                                                               ▼
                                                                       parquet (DuckDB-spatial); columns
                                                                       == proposed PostGIS `observation`
                                                                       → suggestion engine / editor overlay
```

Every source normalises to one **observation** row, so swapping/adding a source never touches
detection or geometry. Mapillary fills it today; GSV and dashcam are later adapters writing the
same shape.

## Files

- **`triangulate.py`** — the network-free geometry core (reused by every source):
  - `enu` / `enu_inv` — local tangent-plane meters (equirectangular; exact enough over a road bbox).
  - `detection_bearing(compass, x_px, width, camera_type, params)` — pixel column + camera pose →
    compass bearing. Handles equirectangular/spherical panos and perspective/fisheye cameras.
    *(The image-center convention + sign of the offset are calibration knobs — verify against
    ground truth before trusting absolute bearings.)*
  - `triangulate(origins, dirs)` — least-squares ray intersection; returns point, RMS spread,
    parallax. Rejects degenerate near-parallel geometry (max pairwise angle < 5°).
  - `triangulate_ransac(...)` — outlier-robust wrapper (bad detections / GPS spikes).
  - `cluster_signs(points, values, headings)` — directional DBSCAN dedup (Pedersen & Torp): merge
    only same-value signs within `eps_m` that face within `head_deg`, so the entering vs leaving
    sign of a speed zone stay distinct.
  - `python3 traffic/signs/triangulate.py` runs a synthetic self-check.
- **`detections_pull.py`** — the **Mapillary adapter + prototype runner**: pulls per-image
  speed-limit detections along a road bbox, decodes each detection's pixel geometry, computes the
  bearing, triangulates per Mapillary `map_feature`, and **scores the recovered position against
  Mapillary's published position**. Reuses `mapillary_signs.py` (`fetch`, `tiles`, `BBOXES`,
  `OBJECT_VALUES`).
- **`compare_osm.py`** — pull a named route's ways from OSM (geometry + `maxspeed` + last-edit
  timestamp via `out meta`), crawl Mapillary along *only that corridor*, triangulate, snap each
  sign to the nearest section, and classify it using **sign-date vs the maxspeed's true age**:
  `agree` / `disagree_osm_stale` (sign newer → fix OSM) / `disagree_check` (maxspeed set after the
  image → re-verify) / `osm_missing` / `off_route`. `--since-months` pre-filters old imagery.
  `maxspeed_since_ms()` / `enrich_maxspeed_age()` read each way's **OSM version history** to find
  when the `maxspeed` value was last *changed* (so a geometry-only edit doesn't look like a fresh
  speed); cached per way in `data/<ref>_msage.json`.
- **`fuse.py`** — the **Bayesian fusion engine**: `fuse(observations, default)` returns
  `(pred, confidence, runner_up, margin, posterior)` from a legal prior × per-source likelihoods
  weighted by freshness + supersession. The QL.51 runner reads triangulated signs + OSM tags +
  prior; `--extra SOURCE:PATH` plugs in any other points source (Waze, MaxBit, GSV). Trust per
  source in `SOURCE_TRUST`; calibration knobs `CONF_TEMP`/`PRIOR_BASE`/`SIGMA_KMH`. OSM ways are
  cached to `data/<ref>_ways.json` (delete to refresh). `--selfcheck` runs the calibration test.
- **`mapillary_signs.py`** — track-1 re-serve (unchanged).

## Data schemas (parquet now, PostGIS later)

Written under `traffic/signs/data/` (gitignored). Column names mirror the proposed `observation`
table in `traffic/lanes/docs/editor-platform.html` so a later `COPY … TO postgres` is a straight
map. Read/joined with **DuckDB spatial** (`ST_*`), consistent with the repo's DuckDB pattern.

`sign_observations.parquet` — one row per per-image detection:
```
image_id, lon, lat, compass_angle, camera_type, bearing_deg,
attr, value, source, observed_at, image_ref, map_feature_id, ref_lon, ref_lat
```
`signs_triangulated.parquet` — one row per deduped physical sign:
```
lon, lat, value, attr, n_views, ray_spread_m, parallax_deg, source,
map_feature_id, ref_err_m, member_image_ids[]
```

## Run the prototype

```bash
# math self-check (no network)
python3 traffic/signs/triangulate.py

# glue self-check (no network)
python3 traffic/signs/detections_pull.py --selfcheck

# live: pull a few tiles of Hanoi, triangulate, score vs Mapillary reference
MAPILLARY_TOKEN=MLY|... python3 traffic/signs/detections_pull.py --bbox hanoi --limit-tiles 4

# a whole named route: crawl + triangulate + compare to OSM (edit-time aware)
MAPILLARY_TOKEN=MLY|... python3 traffic/signs/compare_osm.py --ref QL.51 --since-months 24

# fuse all sources → per-segment value + confidence (no token; uses cached OSM ways)
python3 traffic/signs/fuse.py --selfcheck
python3 traffic/signs/fuse.py --ref QL.51 --signs traffic/signs/data/ql51_signs.parquet \
    --extra waze:traffic/signs/data/waze_sample.parquet
```

Token is free at mapillary.com/dashboard/developers. Success metric: median `ref_err_m` ≲ 5 m
(in line with the directional-clustering literature). A wide error or few decodable views means
the bearing convention or detection decode needs calibration (see the `detection_bearing` note).

## Roadmap (beyond the prototype)

1. **Prototype (done):** Mapillary detections → triangulate → score. Validates the geometry + dedup.
2. **SAM3 detector swap:** crawl raw images (`thumb_2048_url`), SAM3 text-prompt ("speed limit
   sign") → mask + box; crop → value via OCR/small classifier. Same `bearing_ray`/`triangulate`.
   Keep SAM3 outputs as labels for a later fine-tuned detector.
3. **Crawl + DB substrate:** persist images + observations, incremental by road (the "set up a DB"
   step — parquet lake first, PostGIS when O3KR3 locks the schema).
4. **GSV + dashcam adapters:** new source adapters emitting the same observation row shape (dashcam
   gives the best pose/calibration). No downstream change.
5. **Serve:** triangulated signs into the `traffic/lanes/` editor overlay + as `observation` rows
   feeding the suggestion engine. Optional monocular-depth + MRF fusion (Krylov) for single-view
   signs.

## References (verified via scite)

- Krylov, V. A., Kenny, E., & Dahyot, R. (2018). Automatic discovery and geotagging of objects from street view imagery. *Remote Sensing*, 10(5), 661. https://doi.org/10.3390/rs10050661
- Krylov, V. A., & Dahyot, R. (2019). Object geolocation from crowdsourced street level imagery. https://doi.org/10.1007/978-3-030-13453-2_7
- Object geolocation using MRF-based multi-sensor fusion (2018). https://doi.org/10.1109/icip.2018.8451458
- Zhang, C., Fan, H., & Li, W. (2021). Automated detecting and placing road objects from street-level images. *Computational Urban Science*, 1, 18. https://doi.org/10.1007/s43762-021-00019-6
- Geolocating traffic signs using crowd-sourced imagery (2020). https://doi.org/10.1145/3397536.3422340
- Geolocating traffic signs using large imagery datasets (2021). https://doi.org/10.1145/3469830.3470900
- Monocular vision-based crowdsourced 3D traffic sign positioning with unknown camera intrinsics and distortion coefficients (2020). https://doi.org/10.48550/arxiv.2007.04592
- Crowdsourced 3D mapping: a combined multi-view geometry and self-supervised learning approach (IROS 2020). https://doi.org/10.1109/iros45743.2020.9341243
- Pedersen & Torp (2021, directional clustering) · Newson & Krumm (2009, HMM map-match) · He et al. (2020, RoadTagger) — in `archive/research/README.md`.
