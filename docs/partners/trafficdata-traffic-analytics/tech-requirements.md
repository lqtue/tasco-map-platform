# Technical Work Package

# Traffic Analytics & Intersection Digital-Twin Pilot (Vietnam)

*Tasco-authored requirements · 2026-07-06 · Owner: Tuệ*
*Partner self-report: [product-dashboard.csv](product-dashboard.csv) (TrafficData — Macro / SIM / Atlas / Smart Parking)*

## 1. Project Context

Tasco's live traffic work is enriching Vietnam's road network with missing OSM
attributes — **maxspeed, signalized intersections, lane counts** — with
verifiable street-level evidence per edit (see `traffic/` in the repo). TrafficData
offers four products; this pilot scopes the two that fit Tasco's roadmap now, plus
a note on where a third overlaps existing in-house pipelines.

```text
Macro   — RTSP camera flow / classification / incident analytics
SIM     — intersection digital twin + signal-timing optimization
Atlas   — mobile road-asset capture (trained NN) → digital twin       [overlaps in-house]
Parking — smart parking-space detection                               [out of scope for pilot]
```

**Critical caveat, stated up front:** TrafficData's detection models are trained
on a **Russian** dataset — their own success metric caps object detection at
">90% *for road assets present in the Russian dataset*." Vietnam traffic is
motorcycle-dominant with different signs, lane discipline, and vehicle mix. **VN
retraining and VN-specific acceptance are mandatory**, not optional, for every
product below.

## 2. Pilot Geography

### 2.1 Primary City
TrafficData proposes **Ho Chi Minh City** (RTSP camera access + a high-traffic
intersection). Acceptable for the pilot; confirm which HCMC districts have usable
RTSP feeds before committing.

### 2.2 Operating Units

```text
Macro : camera site  (RTSP stream + counting lines + detection zones)
SIM   : one intersection  (geometry, lanes, phases)
Atlas : drivable corridor  (4–8 h of representative video)
```

## 3. Core Problems to Solve

```text
Macro : reliable flow intensity + classification + incident detection, VN-verified
SIM   : an accurate intersection digital twin whose optimized signal plan
        measurably beats the baseline AND is implementable under VN rules
Atlas : road-asset detection accurate on VIETNAMESE signs/assets, geolocated <0.5 m
```

The platform must not deliver black-box dashboards. Tasco requires **VN-validated
accuracy, exportable data, and a handover path** — not a vendor-hosted demo only.

## 4. Required Data & Inputs

Tasco provides (partner resource asks, confirmed):

```text
Macro : RTSP links, camera specs, network access, camera-angle support,
        local context (lane config, high motorcycle share)
SIM   : intersection geometry, lane-use signs, crossings, current signal
        parameters (cycle, phase sequence, yellow/all-red), UAV capture
Atlas : driver + vehicle with roof rails, route guidance for sign density
```

TrafficData provides:

```text
detection platform + models, digital-twin engine, processing service,
neural-net training on the collected VN video
```

## 5. VN Model-Adaptation Requirement (critical)

Because the base models are RU-trained, the vendor must:

```text
- collect 4–8 h representative VN video (Atlas / Macro sites)
- retrain / fine-tune on VN classes: motorcycles, mixed lanes, VN sign set
- report accuracy SEPARATELY for VN classes, not the RU baseline number
- deliver the collected VN dataset to Tasco (dashboard lists this as a deliverable)
```

## 6. Required Deliverables (MVP)

```text
Macro : interactive camera-status map (counting lines + zones),
        flow/type/speed/level-of-service data (exportable),
        incident log with timestamp + visual proof, analytics dashboard, pilot report
SIM   : intersection digital twin (geometry + lane + phase logic),
        baseline performance report, "before vs after" report
        (delay / queue length / capacity)
Atlas : demo access to processed results + the collected VN training dataset
```

## 7. Data Export & Ownership Contract

```text
- all counts / classifications / incidents exportable as CSV/GeoJSON/Parquet
  (not locked in a vendor UI)
- incident and flow records carry timestamp, location, class, confidence
- the collected VN video dataset is delivered to and owned by Tasco
- digital-twin model + optimized signal plans delivered as data, not screenshots
```

## 8. Acceptance Criteria

```text
Macro
  1. RTSP streams connect; data verified by manual audit of video samples.
  2. Incident detection (accident, jam, wrong-way, illegal stop) logged with
     timestamp + visual proof, VN-audited precision/recall reported.
  3. Congestion patterns identified with enough data to feed SIM.
SIM
  1. Digital twin matches real intersection geometry/lanes/phases.
  2. Baseline report identifies real bottlenecks + peak load distribution.
  3. Optimized plan shows measurable delay/queue improvement vs baseline
     AND is implementable under VN safety rules (yellow/all-red honored).
Atlas
  1. Object detection >90% on VN-present assets (NOT only RU classes).
  2. Geolocation error <0.5 m under stable GPS.
  3. 4–8 h VN video collected and delivered.
```

## 9. First Technical Spike (gate before scale)

```text
Duration : ~10 working days
Scope    : ONE Macro camera site + ONE SIM intersection in HCMC
Inputs   : RTSP feed + intersection data + signal params + UAV capture (Tasco)
Outputs  : live camera analytics, VN-audited accuracy, one intersection digital
           twin, baseline + before/after report, exported data samples
PASS if  : streams analyzed with VN-verified accuracy, incidents logged with
           proof, digital twin validated, optimized plan beats baseline,
           data exports cleanly, Tasco receives the VN dataset
FAIL if  : accuracy only demonstrated on RU classes, data locked in vendor UI,
           optimized plan not implementable under VN rules, no dataset handover
```

## 10. Overlap With In-House Work (assess before contracting)

```text
- Atlas road-asset detection overlaps traffic/signs/ (Mapillary sign
  triangulation + Bayesian fusion) — decide buy vs build, avoid paying twice.
- SIM lane/phase data overlaps traffic/lanes/ (the MapOps editor) and the
  lanes/maxspeed enrichment worklist — align schemas, reuse OSM geometry.
- Macro speed/flow is NEW capability (live sensing) — clearest standalone value.
```

## 11. Key Questions for Vendor

```text
1. Which HCMC camera feeds are RTSP-accessible today, and at what resolution?
2. What VN accuracy do you commit to AFTER retraining (per class)?
3. Are all outputs exportable (CSV/GeoJSON/Parquet), or UI-only?
4. Can the digital twin + optimized plans be handed over as data Tasco re-runs?
5. Do you deliver the collected VN training dataset, with what license?
6. Can SIM ingest measurements from Macro, or is each product siloed?
7. Deployment: Tasco-hosted possible, or vendor-cloud only?
```

## 12. Final Expected Outcome

A VN-validated traffic-analytics + intersection-optimization pilot whose data
Tasco owns and can export — live flow/incident sensing (Macro) and a proven
signal-optimization loop (SIM) — with model accuracy demonstrated on **Vietnamese**
traffic, and clear boundaries against the in-house sign/lane pipelines.
