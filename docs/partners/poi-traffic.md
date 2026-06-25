# Partners — POI / Geocoding & Traffic
*[← Index](_index.md) · Updated: 2026-06-25 · Owner: Vũ (POI) · Tuệ (Traffic)*

---

## Evaluation Matrix — POI / Geocoding

| Hard gate | Amazon Location | GrabMaps | TomTom POI |
|---|---|---|---|
| Commercial license + derivative works | ⚠️ TBD | ⚠️ TBD | ⚠️ TBD |
| Vietnam POI coverage | ⚠️ TBD (GrabMaps provider — strong SEA) | ⚠️ TBD | ⚠️ TBD |
| Dedup key stable across sources | ⚠️ `place_id` — TBD cross-source | ⚠️ TBD | ⚠️ TBD |

| Weighted criterion | Weight | Amazon Location | GrabMaps | TomTom POI |
|---|---|---|---|---|
| Results per query (AWS cap = 50) | High | ⚠️ Hard cap; H3 strategy handles it | TBD | TBD |
| Cost per request × VN volume | High | ~$0.50/1k → ~$12,762 VN-wide est. | TBD | TBD |
| Integration with H3 crawl pipeline | High | ✅ Designed | TBD | TBD |
| Freshness | Medium | TBD | TBD | ⚠️ Way ID 2–3 yrs old |

| | Amazon Location | GrabMaps | TomTom POI |
|---|---|---|---|
| **Status** | ⏳ Stage 1→2 | ⏳ Stage 1→2 | ⏳ Stage 1→2 |
| **Rec** | Pending (likely primary) | Pending (assess vs Amazon) | Pending |

---

## Evaluation Matrix — Traffic

| Criterion | TomTom display | Mapillary GPS |
|---|---|---|
| Use for ETA calculation | ❌ No — Way ID 2–3 yrs old, display only | ✅ Yes — feeds Valhalla speed profile |
| Cost | ~$8/1k req | ✅ Free (public) |
| Real-time refresh | ✅ ~5 min | ❌ Historical only |
| Status | ✅ Active (display layer) | ✅ Active (speed profile) |
| Rec | ✅ Continue (display only) | ✅ Continue |

---

## POI / Geocoding

**Strategy:** multi-source crawl + dedup — not a single dataset purchase.
Pipeline: Amazon Location (Grab/GrabMaps provider) + Uber H3 indexing + Google Open Buildings polygons + TomTom → dedup by `place_id` across sources.

**Decision criteria:**
1. Results per query (AWS cap = 50 — H3 resolution strategy already designed)
2. Commercial license + derivative works (storing + serving the data)
3. Per-request cost × Vietnam volume estimate
4. Dedup key stability across providers

---

### Amazon Location Service (provider: GrabMaps)

**Origin:** 🇺🇸 USA / 🇸🇬 SG · **Stage:** Evaluating · **Owner:** Vũ

| Parameter | Status | Notes |
|---|---|---|
| Coverage (Vietnam) | TBD | GrabMaps provider — strong in SEA |
| Results / query | ⚠️ Max 50 | Hard cap; H3 resolution strategy handles this |
| Cost per request | TBD | Vũ to confirm; estimated $0.50/1k → ~$12,762 VN-wide |
| Commercial license | TBD | — |

**Open items:**
- [ ] Vũ: confirm per-request pricing + commercial license terms
- [ ] Run ~$0.05 spot-check on res-12 cells inside dense urban block before bulk run

---

### GrabMaps (direct)

**Origin:** 🇸🇬 Singapore · **Stage:** Evaluating · **Owner:** Vũ

**Open items:**
- [ ] Assess whether direct Grab API gives better terms than via Amazon Location

---

### TomTom

**Origin:** 🇳🇱 Netherlands · **Stage:** Evaluating (POI) + In use (traffic display) · **Owner:** Vũ

| Parameter | Status | Notes |
|---|---|---|
| POI data | TBD | Part of crawl/dedup pipeline |
| Way ID freshness | ⚠️ 2–3 years old | **Do not use for ETA** — display only |
| Traffic display | ✅ In use | ~$8/1k req; 5-min refresh; overlay only |
| Commercial license | TBD | — |

**Open items:**
- [ ] Vũ: confirm POI commercial license terms
- [ ] Huy: confirm TomTom cache cost per volume (current estimate $8/1k req)

---

## Traffic Data

**Strategy:** TomTom for real-time display tiles (already in use); Mapillary public GPS for historical speed profiles fed into Valhalla (free).

---

### TomTom (traffic display)

*See POI section above.* Key constraint: **Way ID is 2–3 years old — must not be used for ETA calculation.** Display map and traffic overlay must share the same Way ID → only use TomTom as a colour overlay on our own base map.

---

### Mapillary (GPS speed profiles)

**Origin:** 🇺🇸 USA (Meta) · **Stage:** In use · **Rec:** ✅ Proceed · **Owner:** Tuệ

- Public GPS traces → `vehicle_type` split (motorcycle vs. car) → Valhalla historical speed profile
- Cost: $0 (public dataset)
- Vietnam coverage at trunk + primary: sufficient for baseline; tertiary sparse

**Open items:** None — already running.
