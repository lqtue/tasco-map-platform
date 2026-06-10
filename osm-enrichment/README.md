# osm-enrichment/

Working folder for the **OSM Traffic Data Enrichment System** (T6 initiative — automatically
detecting and adding missing speed limits, signalized intersections, and lane counts to
OpenStreetMap for Vietnam). This is distinct from the satellite tile-server MVP in the rest of
this repo; it is the current main task plan.

```
osm-enrichment/
├── PROJECT_PLAN.md      ← the proposal / main task plan (v1.0, 2026-06)
└── research/
    └── README.md        ← annotated, scite-verified bibliography backing the three problems
```

**Three core problems** (see `PROJECT_PLAN.md`):
1. Speed limits — legal rule defaults ⊕ Mapillary sign detection.
2. Signalized-intersection detection — street-level imagery, satellite fallback.
3. Lane count — AI detects markings/arrows, geometric/graph rules conclude structure.

Start with `research/README.md`: **RoadTagger (He et al., 2020)** is the keystone reference for the
plan's "AI sees, rules reason" architecture.
