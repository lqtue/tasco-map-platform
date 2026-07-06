# Partnership Tracker — TASCO Mapping Division
*Updated: 2026-06-25 · Owner: Tuệ · [Sat imagery](sat-imagery.md) · [Street view](street-view.md) · [POI & Traffic](poi-traffic.md)*

---

## Pipeline stages

```
1. Prospect → 2. Intro call → 3. Tech eval → 4. Commercial eval → 5. Pilot → 6. Decision → 7. Contract → 8. Active
```

Hard gate at each `→`: must clear before moving forward. Gate fails → **Park** or **Reject**.

---

## Satellite Imagery

| Provider | Model | Stage | Gate / blocker | Owner |
|---|---|---|---|---|
| **CGSTL** | 🤝 Partnership | **2→3** Intro done | ❗ Secrecy / no-attribution clause — unresolved. Blocks everything. | Tuệ |
| **GALAXYSPACE** | 🤝 Partnership | **2→3** Intro done | ❗ Same as CGSTL | Tuệ |
| **UP42** | 🛒 Vendor | **1→2** No contact | Send partner brief + request intro | Vũ |
| **Skywatch** | 🛒 Vendor | **1→2** No contact | Send partner brief + request intro | Vũ |

## 3D Buildings & Demolition Data

| Provider | Model | Stage | Gate / blocker | Owner |
|---|---|---|---|---|
| **ForaSpace** | 🤝 Partnership | **2→3** Work package received | 10-day tech spike (5–10 km² Hanoi) gates contract; ❗ needs Tasco demolition-corridor polygon. Consumes CGSTL imagery — [sat-case link](foraspace-3d-buildings/analysis-sat-case-link.md). | Tuệ |

## Street View & Ground Collection

| Provider | Model | Stage | Gate / blocker | Owner |
|---|---|---|---|---|
| **DigiMe** | 🤝 Partnership | **2→3** Intro done | TASCO to send specific collection targets (~2 wks) | Tuệ |
| **TASCO Crowdsource** | Internal | **3→4** Tech clear | SOP + driver incentive structure — confirm with HR | Tuệ |
| **Mapillary** | 🔌 Data source | **8** Active (sign pipeline) | — | Tuệ |
| **KartaView** | 🛒 Vendor | **1→2** No contact | Assess Vietnam coverage first | Tuệ |
| **Google SV API** | 🛒 Vendor | **1→2** Scoped in OKR | Confirm training data licensing before proceeding | Tuệ |
| **Ryegrass** | 🤝 Partnership | **2→3** Product dashboard received | MMS L-Scan D2 mobile LiDAR → .LAS/.LAZ point clouds + georeferenced 3D building models (≤5 cm RMSE). Team wants to travel to VN. ❗ Needs Tasco tech req ([draft](ryegrass-mobile-mapping/tech-requirements.md)) + SUV/driver/rails/garage + regulatory clarifications. Feeds 3D-buildings (cf. ForaSpace). | Tuệ |

## POI / Geocoding

| Provider | Model | Stage | Gate / blocker | Owner |
|---|---|---|---|---|
| **Amazon Location** | 🛒 Vendor | **1→2** No contact | Confirm per-request pricing + license terms | Vũ |
| **GrabMaps** | 🛒 Vendor | **1→2** No contact | Assess vs. Amazon Location (may be same underlying data) | Vũ |
| **TomTom (POI)** | 🛒 Vendor | **1→2** No contact | Confirm POI license terms | Vũ |

## Traffic

| Provider | Model | Stage | Gate / blocker | Owner |
|---|---|---|---|---|
| **TomTom (display)** | 🛒 Vendor | **8** Active | ⚠️ Way ID 2–3 years old — display only, never ETA | Huy |
| **Mapillary GPS** | 🔌 Data source | **8** Active | — | Tuệ |
| **TrafficData** | 🤝 Partnership | **2→3** Product dashboard received | 4 products: Macro (RTSP camera flow/incident analytics), SIM (intersection digital twin + signal optimization), Atlas (mobile road-asset capture), Smart Parking. Pilot in HCMC. ❗ Needs Tasco tech req ([draft](trafficdata-traffic-analytics/tech-requirements.md)) + RTSP links/camera specs/UAV/signal params. | Tuệ |

---

*Model key: 🤝 Partnership (negotiated long-term) · 🛒 Vendor (buy/subscribe) · 🔌 Data source (free/API) · Internal*
