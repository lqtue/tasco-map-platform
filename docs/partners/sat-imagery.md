# Partners — Satellite Imagery
*[← Index](/_index.md) · Updated: 2026-06-25 · Owner: Tuệ*

**Two distinct procurement models in this category:**
- 🇨🇳 **Chinese providers (CGSTL, GALAXYSPACE):** long-term partnership model — ongoing relationship, not a per-area purchase. Deal structure, exclusivity, and terms are negotiated as a strategic partnership.
- 🌐 **Western providers (UP42, Skywatch):** vendor/client model — TASCO buys imagery by area (per km²), standard commercial terms, no long-term commitment required.

---

## Evaluation Matrix
*Populated at Stage 3→4. Hard gates checked first — any ❌ exits the pipeline regardless of other scores.*

### Hard gates (must all be ✅ to proceed)

| Gate criterion | CGSTL | GALAXYSPACE | UP42 | Skywatch |
|---|---|---|---|---|
| Secrecy — no attribution of source in end products | ⚠️ TBD | ⚠️ TBD | ✅ Standard commercial | ✅ Standard commercial |
| Resolution ≤ 0.5 m GSD | ⚠️ Floor at 0.5m | ⚠️ Floor at 0.5m | ✅ Sub-0.5m available | ✅ Sub-0.5m available |
| Commercial + derivative works license | ⚠️ TBD | ⚠️ TBD | ✅ Standard | ✅ Standard |

### Weighted criteria (after hard gates pass)

| Criterion | Weight | CGSTL | GALAXYSPACE | UP42 | Skywatch |
|---|---|---|---|---|---|
| Vietnam coverage completeness | High | TBD | TBD | TBD | TBD |
| Re-acquisition policy (cloud rejection) | High | TBD | TBD | TBD | TBD |
| Revisit frequency | High | ✅ Good (multi-fleet) | ✅ Good (multi-fleet) | TBD | TBD |
| Archive depth (≥18 months over VN) | Medium | TBD | TBD | TBD | TBD |
| Delivery format (COG + S3) | Medium | TBD | TBD | TBD | TBD |
| Geometric accuracy (CE90 ≤ 5m) | Medium | TBD | TBD | TBD | TBD |
| Price / deal terms | High | Partnership TBD | Partnership TBD | $/km² TBD | $/km² TBD |
| Deal model fit for TASCO | High | ✅ Long-term | ✅ Long-term | ✅ Flexible | ✅ Flexible |

### Current recommendation

| | CGSTL | GALAXYSPACE | UP42 | Skywatch |
|---|---|---|---|---|
| **Status** | ⏸ Blocked on secrecy gate | ⏸ Blocked on secrecy gate | ⏳ Awaiting first contact | ⏳ Awaiting first contact |
| **Rec** | Pending | Pending | Pending | Pending |

---

## CGSTL (Chang Guang Satellite Technology)

**Origin:** 🇨🇳 China · **Stage:** Evaluating · **Rec:** Pending

### Contacts
| Name | Role | Contact |
|---|---|---|
| TBD | TBD | TBD |

### Capabilities confirmed
| Parameter | Status | Notes |
|---|---|---|
| Resolution | ⚠️ ≥ 0.5 m only | Sub-0.5m export blocked by Chinese regulation — not negotiable |
| Revisit time | ✅ Good | Multi-satellite fleet; specific frequency TBD |
| Multi-source | ✅ Yes | Aggregates from multiple satellite sources, not only own fleet |
| Vietnam coverage | TBD | — |
| Archive depth | TBD | — |

### Secrecy / Attribution
- ⚠️ **Not yet confirmed** — critical blocker before proceeding
- Open question: can they deliver through a neutral intermediary (e.g. Singapore reseller)?
- Open question: does COG metadata carry sensor ID / provider name? Can they strip it?

### Meeting Log

#### [Date TBD] — Call 1
*Notes not yet recorded. Verified facts above sourced from this call.*

**Open items:**
- [ ] Confirm secrecy / no-attribution licensing (gates all further evaluation)
- [ ] Get revisit frequency spec sheet
- [ ] Request archive inventory over Vietnam AOI
- [ ] Request pricing (per km², volume tiers)

---

## GALAXYSPACE

**Origin:** 🇨🇳 China · **Stage:** Evaluating · **Rec:** Pending

### Contacts
| Name | Role | Contact |
|---|---|---|
| TBD | TBD | TBD |

### Capabilities confirmed
| Parameter | Status | Notes |
|---|---|---|
| Resolution | ⚠️ ≥ 0.5 m only | Sub-0.5m export blocked by Chinese regulation — same as CGSTL |
| Revisit time | ✅ Good | Specific frequency TBD |
| Multi-source | ✅ Yes | Aggregates from multiple sources |
| Vietnam coverage | TBD | — |
| Archive depth | TBD | — |

### Secrecy / Attribution
- ⚠️ **Not yet confirmed** — same critical blocker as CGSTL

### Meeting Log

#### [Date TBD] — Call 1
*Notes not yet recorded. Verified facts above sourced from this call.*

**Open items:**
- [ ] Confirm secrecy / no-attribution licensing (gates all further evaluation)
- [ ] Get revisit frequency spec sheet + archive inventory + pricing

---

## UP42

**Origin:** 🇩🇪 Germany (Airbus subsidiary) · **Stage:** Evaluating · **Rec:** Pending

### Contacts
| Name | Role | Contact |
|---|---|---|
| TBD | TBD | TBD |

### Capabilities confirmed
| Parameter | Status | Notes |
|---|---|---|
| Resolution | ✅ Sub-0.5m available | Pléiades / SPOT / Airbus OneAtlas |
| Secrecy / attribution | ✅ No mandatory attribution | Standard commercial licensing |
| Vietnam coverage | TBD | — |
| Archive depth | TBD | — |

### Meeting Log
*No meetings yet.*

**Open items:**
- [ ] Request quote for ~20,350 km² initial envelope
- [ ] Request archive inventory over Vietnam AOI at ≤ 0.5 m / ≤ 18 months
- [ ] Confirm re-acquisition policy for cloud-rejected scenes

---

## Skywatch

**Origin:** 🇨🇦 Canada · **Stage:** Evaluating · **Rec:** Pending

### Contacts
| Name | Role | Contact |
|---|---|---|
| TBD | TBD | TBD |

### Capabilities confirmed
| Parameter | Status | Notes |
|---|---|---|
| Resolution | ✅ Sub-0.5m available | Multi-provider marketplace |
| Secrecy / attribution | ✅ No mandatory attribution | Standard commercial licensing |
| Vietnam coverage | TBD | — |
| Archive depth | TBD | — |

### Meeting Log
*No meetings yet.*

**Open items:**
- [ ] Request quote + archive inventory
- [ ] Confirm re-acquisition policy
