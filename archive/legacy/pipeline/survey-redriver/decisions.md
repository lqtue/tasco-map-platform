# MVP pipeline parameters (locked 2026-05-25)

- **AOI:** MGRS tile **T48QWJ** — bbox `105.0,20.71,106.06,21.70` (~110×110 km, covers all of greater Hanoi).
- **Date range:** 2025-05 → 2026-05 (12 months).
- **Cloud filter:** `--max-cloud 60`. Yields 12 of 13 months (Feb 2026 unusable at 80% minimum).
- **Sensors:** HLS S30 + L30, least-cloudy-per-month across both.
- **Outputs (both produced, plugin shows both lists, user picks one to load):**
  - Per-scene COG: `scenes/{scene_id}.tif`
  - Monthly cloud-free composite: `composites/{YYYY-MM}.tif`
- **Tile pyramid:** z0–z14 (native HLS resolution; no upscale).
- **R2 layout:**
  - `tiles/sentinel2/scene/{scene_id}/{z}/{x}/{y}.png`
  - `tiles/sentinel2/monthly/{YYYY-MM}/{z}/{x}/{y}.png`
  - `state.json` keyed by `(source, kind, key)` → `{cog_sha256, tile_count, uploaded_at}` for re-run dedup.
- **Serve:** Static R2 + Nginx. Drop TiTiler from `config/` (no on-demand rendering needed for MVP).

## Coverage survey result (max-cloud=100, 2025-05..2026-05, both sensors)

| Month   | best cloud% | sensor winner |
|---------|-------------|---------------|
| 2025-05 | 13          | S30           |
| 2025-06 | 26          | S30           |
| 2025-07 | 35          | L30           |
| 2025-08 | 55          | S30           |
| 2025-09 | 34          | S30           |
| 2025-10 | 38          | L30           |
| 2025-11 | 3           | S30           |
| 2025-12 | 30          | L30           |
| 2026-01 | 11          | S30           |
| 2026-02 | 80          | S30 (skip)    |
| 2026-03 | 54          | S30           |
| 2026-04 | 11          | S30           |
| 2026-05 | 23          | L30           |

## Known bug to fix during pipeline work

`acquire.py` STAC path uses `query.eo:cloud_cover.lte` which CMR STAC silently ignores → 0 results. Use CMR JSON path, or filter client-side after retrieval.
