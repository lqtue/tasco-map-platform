# Partners — Street View
*[← Index](_index.md) · Updated: 2026-06-25 · Owner: Tuệ*

> **Two distinct partner types in this file:**
> - **Ground collection services** (DigiMe, TASCO Crowdsource) — active field collection; partnership or internal
> - **Imagery archives / APIs** (Mapillary, KartaView, Google SV) — existing datasets accessed via API; vendor/data source

---

## Evaluation Matrix
*Two sub-categories with different criteria. Hard gates checked first — any ❌ exits pipeline.*

### A — Ground collection services (DigiMe, TASCO Crowdsource)

| Hard gate | DigiMe | TASCO Crowdsource |
|---|---|---|
| Vietnam trunk + primary coverage achievable | ✅ Yes (south strong, north TBD) | ✅ Yes (VETC fleet) |
| Data ownership belongs to TASCO | ⚠️ TBD — must confirm in contract | ✅ Fully owned |
| Evidence-based collection (photo proof per point) | ✅ Yes — enforced policy | ✅ Per scope pivot mandate |

| Weighted criterion | Weight | DigiMe | TASCO Crowdsource |
|---|---|---|---|
| Coverage speed — trunk+primary | High | ⚠️ 50–120 active collectors | ✅ ~300 drivers + VETC scale |
| North Vietnam coverage | High | ⚠️ Weaker | ✅ VETC nationwide |
| SOP / methodology maturity | High | ✅ 6 years, proven with Tier 1 clients | ⚠️ Building (QL51 pilot done) |
| Upload model compatibility | Medium | ⚠️ Active (intentional) only — conflict with TASCO passive plan | ⚠️ Passive planned |
| Cost | High | TBD | Incentive + storage only |
| Integration effort | Medium | Medium — SOP alignment needed | Low — internal |

| | DigiMe | TASCO Crowdsource |
|---|---|---|
| **Status** | ⏳ Awaiting TASCO collection targets | ⏳ SOP + HR sign-off pending |
| **Rec** | Pending | ✅ Proceed (primary strategy) |

---

### B — Imagery archives / APIs (sign detection pipeline)

| Hard gate | Mapillary | KartaView | Google SV API |
|---|---|---|---|
| Vietnam trunk + primary coverage | ⚠️ TBD depth | ⚠️ TBD | ✅ Expected |
| API: lat/lng + image ID + heading | ✅ In use | ⚠️ TBD | ✅ Yes |
| License: commercial + AI training on extracted data | ⚠️ Confirm for training | ⚠️ TBD | ⚠️ Raw images blocked — extracted metadata TBD |

| Weighted criterion | Weight | Mapillary | KartaView | Google SV API |
|---|---|---|---|---|
| Sign coverage (speed + khu dân cư + cấm vượt) | High | ✅ Pipeline live | TBD | TBD |
| Image freshness (≤ 2 years) | Medium | ⚠️ Mixed | TBD | ✅ Generally fresh |
| Cost | High | ✅ Free | TBD | ⚠️ Per-request (TBD) |
| Integration effort | Medium | ✅ Already integrated | High | Medium |

| | Mapillary | KartaView | Google SV API |
|---|---|---|---|
| **Status** | ✅ Active — sign pipeline running | ⏳ Not yet assessed | ⏳ Licensing gate must clear first |
| **Rec** | ✅ Continue | Pending | Pending |

---

## DigiMe

**Website:** digime.asia · **Origin:** 🇻🇳 Vietnam (SEA operations) · **Stage:** Evaluating · **Rec:** Pending
**Connected via:** Khánh · **Main contact:** Phong (Head of Innovation / CEO)

### Profile
6-year-old geospatial data collection and map maintenance company operating across SEA (Vietnam, Indonesia, Philippines, Thailand, Malaysia). Current clients include Google Maps, Apple Maps, TomTom, HERE. Core thesis: **map maintenance** (not building) is the hard, defensible work.

### Capabilities
| Parameter | Status | Notes |
|---|---|---|
| Vietnam coverage | ✅ Strong (south) | Distributed contractor network, stronger in HCM than Hanoi |
| Collection method | ✅ Mixed | ~50% smartphone, ~50% dedicated cameras (360, dash cam, custom firmware) |
| Active contractors | ⚠️ 50–120 (active) | 500–700 historical total; seasonal / weather-dependent |
| SEA presence | ✅ Yes | Vietnam + Indonesia, Philippines, Thailand, Malaysia |
| Survey permit | ✅ Yes | Official government mapping permit; not well recognized by local authorities in practice |
| AI in pipeline | ✅ Moderation only | Fully automated moderation; **no AI data synthesis** — all data needs physical evidence/photo |
| Data schema | Custom / wide | Proprietary schema supporting multiple client formats; many columns, client-specific |
| Own map product | ✅ OSM fork | Forked OSM 2 years ago; own data layer on top; A2B Navigation app (Android / CH Play) |
| Passive upload | ⚠️ Rejected | Tried passive upload (auto-on-WiFi); raw data storage ballooned with no return. Switched to active (intentional) upload. |

### Partnership angles discussed
- DigiMe provides ground collection methodology + tooling + existing contractor network
- TASCO provides scale: VETC driver fleet (millions of vehicles) + user base + data infrastructure
- Not direct competition: DigiMe is B2B data provider; TASCO is building consumer + platform map
- Specific ask from Phụng: speeding up road network coverage + POI in complex indoor spaces
- DigiMe interest: using TASCO's driver network + QA testing infrastructure

### Key notes
- DigiMe collects **evidence-first**: every data point needs a photo or logged source; clients audit randomly and will reject data without proof. Aligns with TASCO's "evidence per edit" mandate.
- Their active upload model (not passive) may conflict with TASCO's planned passive crowdsource approach — worth aligning on this before committing to a joint collection workflow.
- Long-term B2B commitment is their model: data freshness decays in 3–6 months, so one-off deals don't work for them.

### Meeting Log

#### [Date TBD] — Intro call (via Khánh)
**Attendees:** Phụng (TASCO Head of Mapping) · Phong (DigiMe Head of Innovation / CEO) · DigiMe team
**Key points:**
- Both sides introduced; DigiMe described 6 years in SEA map maintenance for Google/Apple/TomTom/HERE
- Phụng outlined TASCO's goal: national map platform + just-in-time driver alerts; base from VETC 4.2M customers
- DigiMe: mix of smartphone + camera hardware collection; 50–120 active contractors; custom firmware for dash cams
- DigiMe: AI for moderation only, never for data synthesis — always need physical evidence; fully automated now after 7 years of manual data as training set
- DigiMe: tried passive upload → storage bloat, no return; switched to active/intentional upload
- Discussed: using TASCO's VETC driver fleet as a collection network with DigiMe's tooling/SOP
- Discussed: POI collection in complex indoor spaces (malls, towers) + speed limit road attribute collection
- DigiMe: not competing on consumer app (A2B Navigation is a B2B showcase tool, not revenue); B2C organic only
- Phụng flagged: TASCO has millions of vehicles vs DigiMe's 50–120 — scale advantage is TASCO's
**Commitments from DigiMe:** Ready to work together once TASCO provides specific targets
**Open items:**
- [ ] Phụng / Tuệ: provide specific collection targets (which roads, which attributes — speed limits first) → 2-week timeline
- [ ] Align on active vs. passive upload model before committing to joint collection workflow
- [ ] Clarify data ownership terms: if TASCO drivers collect using DigiMe tooling, who owns the resulting data?
- [ ] DigiMe: share data schema sample and pricing model
**Next step:** TASCO to send specific target list (~2 weeks from meeting date); DigiMe to respond with proposal

---

## TASCO Crowdsource (internal)

**Origin:** Internal · **Stage:** Planned · **Rec:** ✅ Proceed

Primary collection strategy. ~300 active VETC/Tasco drivers on national road network.
- **Cost:** driver incentive + ~15 TB storage (no external purchase)
- **Coverage:** trunk + primary in ~weeks; tertiary in ~months
- **Licensing:** fully owned, no restrictions

**Open items:**
- [ ] SOP finalized (Tuệ + Quân — QL51 pilot done)
- [ ] Driver onboarding + incentive structure confirmed with HR

---

## Mapillary

**Origin:** 🇺🇸 USA (Meta) · **Stage:** Evaluating · **Rec:** Pending

### Contacts
| Name | Role | Contact |
|---|---|---|
| TBD | TBD | TBD |

### Notes
- Public GPS traces already in use for Valhalla speed profiles ($0)
- Sign detection API (Map Features) already feeds `traffic/signs/mapillary_signs.py`
- Question: Vietnam road coverage depth at trunk/primary level?
- Commercial license for training data / derivative sign extraction — needs confirmation

### Meeting Log
*No meetings yet.*

**Open items:**
- [ ] Assess Vietnam coverage at trunk + primary (Overpass vs. Mapillary coverage map)
- [ ] Confirm commercial license for AI training on extracted imagery

---

## KartaView

**Origin:** 🇷🇴 Romania (GRAB / HERE ecosystem) · **Stage:** Evaluating · **Rec:** Pending

### Contacts
| Name | Role | Contact |
|---|---|---|
| TBD | TBD | TBD |

### Meeting Log
*No meetings yet.*

**Open items:**
- [ ] Assess Vietnam coverage
- [ ] Confirm API access + licensing terms

---

## Google Street View API

**Origin:** 🇺🇸 USA · **Stage:** Evaluating · **Rec:** Pending

### Notes
- Already in scope via O3KR2: `GSV API → [Editor Spatial DB Server: lat, lon, type, value, source, date]`
- Cost: per-request (volume pricing TBD with Vũ)
- Licensing: commercial use permitted; no training data use without separate agreement — **check carefully**

### Open items
- [ ] Confirm whether extracted sign metadata (not raw images) is permitted for training
- [ ] Get per-request pricing estimate at Vietnam trunk+primary scale
