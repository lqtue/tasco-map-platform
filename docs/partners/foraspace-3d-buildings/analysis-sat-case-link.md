# ForaSpace 3D-Building Pilot ↔ Satellite-Imagery Case

*Analysis · 2026-07-06 · Owner: Tuệ*
*Source: [ForaSpace_Technical_Work_Package_Hanoi_3D_Building_Data_Pilot.pdf](ForaSpace_Technical_Work_Package_Hanoi_3D_Building_Data_Pilot.pdf)*

## What ForaSpace is

A vendor **technical work package** for a *Hanoi 3D Building Data, Demolition
Detection, and 3D Map-Tile API* pilot. Not a pure 3D-rendering job — it is a
**building-data lifecycle + QA platform**: ingest OSM / Google Open Buildings /
TUM GlobalBuildingAtlas, conflate to canonical building IDs, assign each
building a **lifecycle state** (`active` / `demolished_candidate` /
`demolished_verified` / `new_construction_candidate` / …), a **confidence
score** (footprint / height / **freshness** / **demolition** / overall), and a
render policy → LoD1 3D Tiles + MVT + a QA dashboard. Tasco owns the code,
schema, and pipeline (handover, no vendor lock-in). First AOI = 1–3 dense Hanoi
districts; a 10-day, 5–10 km² **technical spike** gates the full contract.

## Why it matters to the sat case

The sat demo (CGSTL/GALAXYSPACE AOI selection) and ForaSpace are **two ends of
the same pipeline**, joined at **demolition / freshness**:

```
CGSTL/GALAXYSPACE  →  fresh Hanoi imagery over demolition corridors
                      ↓  (this is ForaSpace's "recent imagery" / temporal-raster input)
ForaSpace          →  detects demolished buildings, flags stale OSM/Google/TUM,
                      serves clean 3D tiles + QA queues
```

Concretely:

### 1. ForaSpace is the *demand justification* for the CGSTL buy
ForaSpace's demolition detection **requires recent satellite imagery** as
evidence (§4.1 required MVP source, §7.1 rule 6, §8.3 freshness inputs). Its
`freshness_confidence` and `demolition_confidence` degrade without a current
image. **The imagery CGSTL provides is exactly that input.** So the sat
procurement isn't a standalone cost — it feeds a second partner deliverable.
Pitch the two together to the boss/CGSTL.

### 2. ForaSpace resolves the sat demo's "ongoing demolish" gap
The sat demo's demo/trial is anchored to "Hanoi urban with ongoing demolition"
but **has no demolition layer** — we've been seeding on built-up density as a
proxy. ForaSpace has the **same gap** and its answer is the same ask: §2.4 /
§13.3 both say *"Tasco-provided road-corridor or demolition polygon if
available."* → **Both partners need the boss's demolition-corridor polygons.**
Sourcing them once (VnExpress 1,428-project clearance campaign: Ring Road 1
Hoàng Cầu–Voi Phục, RR 2.5/3/3.5/4, Red-River bridges, West Lake, Tây Tựu, Hoàng
Mai health complex) pins the seed for **both** the sat AOI demo and the ForaSpace
spike AOI.

### 3. Shared AOI unit → align the two deliverables
ForaSpace's suggested first districts (§2.3): **Ba Đình, Hoàn Kiếm, Đống Đa,
Hai Bà Trung, Cầu Giấy, Thanh Xuân, Hoàng Mai, Long Biên**. The sat demo
currently seeds on the densest Hà Nội H3 hex (central Hanoi ≈ 105.83/20.99),
which falls inside this set. **Adopt this district list as the sat demo's AOI
tier options** so the imagery footprint and the 3D-building AOI describe the
same ground — one story for the boss.

### 4. Data flows the other way too
The sat demo already emits an **AOI tasking-footprint** GeoJSON + archive mask.
That footprint = *where CGSTL captures* = ForaSpace's ingestion extent. The sat
bundle can be handed to ForaSpace as the pilot's imagery-coverage definition.

## Concrete next steps

| # | Action | Serves |
|---|---|---|
| 1 | Ask boss for the demolition-corridor polygon(s) — Ring Road 1 Hoàng Cầu–Voi Phục first | sat demo seed **+** ForaSpace spike AOI |
| 2 | Re-seed the sat demo demo/trial on that polygon once received (today it's density-proxy) | sat demo |
| 3 | Adopt ForaSpace's 8-district list as the sat AOI tier presets | aligns both |
| 4 | Bundle-pitch: "CGSTL fresh imagery → ForaSpace demolition QA" as one procurement story | commercial |
| 5 | Add ForaSpace to the partner tracker; treat as stage 2→3 (tech-eval on the spike) | tracking |

## Not a fit / watch-outs

- ForaSpace is a **3D-buildings** workstream, **not** satellite imagery — it does
  not replace CGSTL, it consumes CGSTL's output. Keep them separate rows on the
  tracker, linked by the demolition spine.
- ForaSpace wants **Tasco-owned, re-runnable** infra (no vendor hosting in prod).
  Same handover posture we want from CGSTL — consistent negotiating line.
- The spike is the real gate (§13.5 PASS/FAIL). Don't commit district-scale
  scope before the 10-day spike proves demolition detection + reproducibility.
