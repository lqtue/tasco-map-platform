# AWS Reverse-Geocode Crawl — H3 Resolution Analysis

**Data:** `untitled-3.geojson` — Khánh Hội ward, D4 HCM; 513 cells at res-9/10/11 (run by Vũ)  
**Date:** 2026-06-18  
**Context:** PRD at tascomaps.atlassian.net/wiki/spaces/GSPA/pages/6849211

---

## Key finding: res-11 is structurally marginal in dense urban areas

Every single cell in the D4 sample hit the AWS 50-result cap at all resolutions tested (res-9, 10, 11). The cause is geometric, not a data issue:

```
H3 res-11 circumradius  =  29 m
AWS 50th-result radius  =  28 m  (observed median in Khánh Hội)
```

These are nearly equal. A building at a cell vertex is 29 m from the nearest cell center — right at the edge of the AWS search radius. It may rank 50th or 51st depending on what else is nearby. **73% of unique places in the sample appear in only one cell**, meaning any missed result drops that place entirely.

---

## Calibrated multiplier

Open Buildings has one centroid per building footprint. AWS returns all named places inside (units, businesses, address points).

| Measurement | Value |
|---|---|
| Local place density (from AWS observation) | 50 results / π×28² m² = **0.0203 places/m²** |
| OB building density in D4 | **0.0044 buildings/m²** |
| Implied multiplier | **4.6 places/building** (ultra-dense urban) |

This multiplier is area-dependent. Suburban and rural areas are much lower (closer to 1–2).

---

## Resolution selection rule

A cell is safe when all buildings within its circumradius rank ≤ 50 in the AWS response, i.e. the circumradius is comfortably inside the AWS search radius.

| Resolution | Edge | Circumradius | vs AWS 28 m | Coverage |
|---|---|---|---|---|
| res-11 | 25 m | 29 m | ≈ equal | **Marginal** — vertex buildings at risk |
| res-12 | 9 m | 10 m | << 28 m | **Complete** — every building within 10 m of a center |
| res-13 | 3.5 m | 4 m | << 28 m | Overkill for coverage |

**Threshold to upgrade from res-11 → res-12:**  
`buildings/res-11 cell > 9`  (calibrated: 9 × 4.6 × π×29²/2160 ≈ 50 expected places in search radius)

At this density, 25.2% of HN+HCM res-11 cells need upgrading.

---

## Cost model (HN + HCM, $0.50/1k calls)

| Strategy | Calls | Cost | Notes |
|---|---|---|---|
| Pure res-11 | 1,202,511 | **$601** | Incomplete — dense areas truncated |
| Adaptive res-11/12 (threshold = 9 bldg/cell) | 3,222,273 | **$1,611** | Complete coverage |
| Pure res-12 | 8,417,577 | **$4,209** | 7× overkill for sparse areas |

The adaptive plan: 72% of cells stay at res-11 ($433), 28% upgrade to res-12 ($1,178).

---

## Do we need res-13?

Expected results per res-12 cell in Khánh Hội density:

```
π×28² / 309 × 50  ≈  6 results/cell
```

Far below the 50-result cap. Res-13 is not needed as a grid-level resolution.

The only exception: a single building with hundreds of units (large mall, 30+ floor apartment tower) where a res-12 cell still hits 50. These would be spotted as outliers in Vũ's res-12 run and can be patched with 7 res-13 children each — negligible cost.

---

## Recommended next step for Vũ

Run the **49-cell res-12 patch** over the densest spot in the existing sample to validate:

- **Center:** `(10.75821, 106.70653)` — tightest spot in D4 sample (50th result at 13 m)
- **How:** expand the densest res-11 cell `8b65b5660c05fff` + its 6 neighbors to res-12 children
- **Cost:** $0.02
- **Check:** if max `result_rank` < 50 across the 49 cells → res-12 confirmed sufficient

Full Khánh Hội ward at res-12: **3,087 cells → $1.54** — also cheap enough to run completely.

---

## Summary

| Question | Answer |
|---|---|
| Why does res-11 truncate in D4? | Circumradius (29 m) ≈ AWS search radius (28 m) — geometric coincidence |
| What resolution fixes it? | **res-12** (circumradius 10 m << 28 m) |
| Upgrade threshold | > 9 OB buildings per res-11 cell |
| Total cost HN+HCM (adaptive res-11/12) | **~$1,600** |
| Need res-13? | No — unless specific outlier buildings hit 50 at res-12 |
