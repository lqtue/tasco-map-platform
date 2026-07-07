# ForaSpace Hà Nội 3D Building — QC Report

Independent quality-control of the ForaSpace-delivered 3D building model (Ba Đình pilot AOI), cross-checked against Google (Google Open Buildings), TU Munich (GlobalBuildingAtlas), Overture, and OpenStreetMap, and evaluated against the [Technical Work Package](../ForaSpace_Technical_Work_Package_Hanoi_3D_Building_Data_Pilot.pdf).

- **`ForaSpace_QC_Hanoi.html`** — interactive report, VI/EN/RU switcher, self-contained (open in any browser).
- **`ForaSpace_QC_Hanoi.pdf`** — printable version for sharing.

## Headline findings (AOI: Ba Đình, bbox 105.830–105.849 E / 21.030–21.045 N)

| Aspect | Verdict |
|---|---|
| Provenance | Raw OpenStreetMap extract (blender-osm); only 1.6% of OSM buildings carry a real height tag |
| Geometry | **Pass** — clean LoD1 extrusion; minor cleanup (167 degenerate faces, 2.3% footprint overlap in ~22 nested-container clusters) |
| Height | **Fail** — 96% are the exporter default (9.0 m OBJ / 4.5 m GLB). Three independent satellite sources agree true median ≈ 10–12 m (TU Munich 10.1 m, Google 11.75 m, Overture 12.3 m). Per-matched error −5.4 m, RMSE 7.3 m, 94% too short |
| Completeness | **Incomplete** — ForaSpace 8,184 buildings = 62% of Google (13,299), 77% of TU Munich (10,601), 76% of Overture (10,746) → missing ~25–40%, mostly small alley houses (footprint sizes otherwise match: median 45 m² ≈ TU Munich 43 m²) |
| Spec / architecture | Delivered file = stage-1 (OSM → LoD1 → tiles). **Gap:** the two height sources the spec requires (TU Munich, Google 2.5D Temporal) are absent from the vendor's integration list → `height_confidence` (§8.2) can't be computed; conflation/lifecycle/API layers are MVP-claimed but not verifiable from the file |

## Reproduce

Analysis scripts + intermediate data live in the session scratchpad (not committed). Method: parse OBJ/GLB geometry, georeference from GLB `origin`/`bbox` extras (verified ±2 m), pull references via Overpass (OSM), DuckDB over source.coop GeoParquet (TU Munich), Earth Engine (Google Open Buildings v3 + 2.5D Temporal), and DuckDB over S3 (Overture); match footprints with a Shapely STRtree.
