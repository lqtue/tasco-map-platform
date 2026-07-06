# Technical Work Package

# Hanoi Mobile-Mapping (MMS LiDAR) — 3D Building & Facade Capture Pilot

*Tasco-authored requirements · 2026-07-06 · Owner: Tuệ*
*Partner self-report: [product-dashboard.csv](product-dashboard.csv) (Ryegrass, MMS L-Scan Premium D2)*

## 1. Project Context

Tasco is building a 3D Building Data Platform for a production mapping platform
in Vietnam. The first area is Hanoi, which is undergoing active urban change —
roads widened, buildings demolished (Ring Road 1 Hoàng Cầu–Voi Phục and the
1,428-project clearance campaign). Global/open building datasets (OSM, Google
Open Buildings, TUM GlobalBuildingAtlas) are **stale** and cannot be trusted for
current ground truth.

Ryegrass proposes **high-speed mobile laser scanning (MMS L-Scan Premium D2)** to
capture high-density 3D point clouds + panoramic facade imagery, and to derive
georeferenced 3D building models.

This pilot is therefore **the fresh ground-truth capture layer** for the 3D
building platform. Its output validates and corrects the conflated building
database (see the ForaSpace 3D-building pilot, which consumes recent ground/air
evidence for demolition and freshness confidence). It is **not** just a point
cloud delivery — it must integrate into Tasco's canonical building database with
lineage.

## 2. Pilot Geography

### 2.1 Primary City
Hanoi, Vietnam.

### 2.2 Operating AOI Unit
Legacy Hanoi urban districts / Quận, aligned with the 3D-building pilot:

```text
Ba Đình, Hoàn Kiếm, Đống Đa, Hai Bà Trưng,
Cầu Giấy, Thanh Xuân, Hoàng Mai, Long Biên
```

Deliver both legacy district and current ward attribution
(`legacy_district`, `current_ward`) — see the ForaSpace work package §2.2.

### 2.3 Recommended First AOI
A drivable urban corridor loop of **10–20 km of streets** inside 1–2 of the
districts above. Must include:

```text
- one active road-widening / demolition corridor (Ring Road 1 first choice)
- one dense tube-house street canyon (facade-capture stress test)
- one wide boulevard with mixed high-rise (height/range stress test)
```

## 3. Core Problem to Solve

Deliver **georeferenced, QA'd 3D building geometry + facades** that Tasco can:
1. treat as ground truth to confirm/deny stale open-dataset buildings, and
2. ingest into the canonical building store with per-object lineage and accuracy.

A point cloud with no georeferencing contract, no accuracy report, and no
integration path is **not acceptable** — it must be reproducible and Tasco-owned.

## 4. Required Data Sources & Capture

```text
MMS LiDAR point cloud (the D2 sensor)
panoramic / facade imagery (co-registered to the cloud)
GNSS + IMU trajectory (post-processed kinematic)
GNSS base-station / VRS / CORS correction used for the survey
```

Tasco provides (Ryegrass resource asks, confirmed):

```text
SUV/pickup + driver, compatible roof rails, secure garage
route selection guidance (max facade + demolition-corridor density)
local admin boundary + road network reference
```

## 5. Required Coordinate & Datum Contract (critical)

Vietnam's legal datum is **VN-2000**; global tiles use **WGS84 / EPSG:4326**;
metric work uses **UTM 48N (EPSG:32648)**. The vendor must state and deliver:

```text
- capture datum + geoid model
- delivered CRS (require BOTH VN-2000 and EPSG:32648, plus a WGS84 export)
- the local→geographic transform + origin offset for any local-coordinate mesh
```

> Watch-out: the ForaSpace mesh sample arrived in **local coordinates with no
> georeference**. Do not accept a Ryegrass deliverable with the same gap — the
> georeferencing contract above is a hard acceptance gate.

## 6. Canonical Deliverable Model

Every delivered building object must carry:

```text
tasco_building_id          (Tasco-issued, stable)
geom_3d                    (LoD2 model, textured where facade imagery allows)
point_cloud_ref            (link to source .LAS/.LAZ tile)
height_m, min_height_m
legacy_district, current_ward
absolute_accuracy_rmse_m   (per route/tile)
completeness_flag          (full / partial / shadow_zone)
capture_date
trajectory_ref
source_lineage             (sensor, pass, correction source)
```

## 7. Required Deliverables (MVP)

```text
1. Raw + processed point clouds        .LAS / .LAZ, classified
2. Georeferenced trajectories          post-processed
3. LoD2 3D building models             georeferenced, integrated to a GIS/PostGIS DB
4. Facade imagery                      co-registered, privacy-reviewed
5. Final QA/QC report                  methodology + accuracy assessment
6. Integration package                 formats + import recipe into Tasco GIS
```

## 8. Acceptance Criteria

```text
1. Absolute point-cloud RMSE ≤ 5 cm on surveyed urban routes under stable GNSS.
2. 100% coverage of agreed roads + target facades; shadow zones flagged, not silent.
3. Delivered in VN-2000 AND EPSG:32648, with a documented transform.
4. 3D building models import into Tasco's GIS/PostGIS without manual repair.
5. Every object carries id, accuracy, completeness, capture date, lineage.
6. GNSS-degraded segments (tunnels, canyons) are flagged with a relative-accuracy note.
```

## 9. First Technical Spike (gate before district-scale contract)

```text
Duration : 3–5 field + processing days
AOI      : one 10–20 km Hanoi urban loop (must include a demolition corridor)
Inputs   : Tasco vehicle/driver/rails + route plan + admin/road reference
Outputs  : classified .LAS/.LAZ, trajectory, LoD2 models for the loop,
           accuracy report, sample facade imagery, integration package
PASS if  : RMSE ≤5cm proven, correct georef in VN-2000+UTM48N,
           models import into Tasco GIS, lineage + accuracy per object,
           Tasco can re-import independently
FAIL if  : local coords only / no accuracy report / no integration path /
           facade imagery with unresolved privacy exposure
```

## 10. Ownership, Handover & Legal

Tasco must own:

```text
delivered point clouds, models, trajectories, and imagery
the CRS/transform definitions
the import/integration recipe
```

Regulatory clarifications the vendor raised (resolve before field work):

```text
- Vietnam permits for mobile LiDAR + street-level imagery capture
- data localisation / export rules for geospatial data
- personal-data handling for facade imagery (faces, plates → blur before delivery)
- any survey/mapping licensing required of a foreign operator
```

## 11. Key Questions for Vendor

```text
1. What absolute accuracy do you guarantee without RTK/VRS in Hanoi canyons?
2. Which correction source (CORS/VRS) will you use, and is it available in VN?
3. LoD level of the delivered building models — LoD1, LoD2, textured?
4. Output formats for models (CityGML, 3D Tiles, OBJ, glTF)?
5. Do you deliver in VN-2000, or only WGS84/local — and who supplies the transform?
6. How is facade imagery privacy-processed before handover?
7. Can Tasco re-run classification/model generation from the raw cloud?
8. Throughput: km of street per field day at target density?
```

## 12. Final Expected Outcome

A reproducible, georeferenced Hanoi mobile-mapping dataset — point clouds, LoD2
building models, and facade imagery — that Tasco owns and can ingest as **fresh
ground truth** into the canonical 3D building database, closing the loop with the
ForaSpace demolition-detection pilot and the satellite-imagery freshness layer.
