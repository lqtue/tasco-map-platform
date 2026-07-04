# MapOps System Architecture — Pre-read (2026-07-01 PM)

**Purpose:** align on the data model before the afternoon discussion. Sources: note_017 transcript + prior MapOps brainstorm. One decision to lock: **the ID/sync contract**. Everything else follows from it.

---

## 1. The model in one picture

```
                    ┌─────────────────────────────┐
   signs/fuse   ──► │   POSTGRES = single truth    │ ◄── contributor / editor edits
   pipeline         │  features + attrs[public|private] + stable_id
   (suggestions)    └──────────────┬──────────────┘
                                   │ generate (versioned: data-ver + config-ver)
                    ┌──────────────┴───────────────┐
                    ▼                               ▼
          ROUTING PBF (class 3–7)          MAPTILE PBF (class 1 + POI/3D)
                    │                               │
              Valhalla (routing)            Martin/tiles + search + nav-test
                    │                               │
                    └──────── weekly sync cycle ────┘   ← version-pair lock

   Publish gate:  per-changeset  →  push to OSM (public)  |  hold internal (private)
```

**Two "geodb" = two derived PBF services, one source (Postgres).** Not two sources of truth. OSM is an external *publish target* for road geometry + public attributes — not a co-equal DB.

- **Routing artifact** — road network only (Valhalla reads root network). Updates fast.
- **Maptile artifact** — everything else: buildings, 3D (CityGML), POI, satellite. Lags ~2 weeks today.

---

## 2. Decisions already implied (confirm or reject)

| # | Decision | Source |
|---|---|---|
| D1 | Postgres is single source of truth; both PBFs are **derived**, versioned (data-ver + config-ver). | transcript L21,27,29 |
| D2 | Public/private is a **per-attribute + per-changeset** flag. Public → OSM, private → internal PBF only. | transcript L7,29 |
| D3 | Push to OSM is **changeset-gated**: choose which changesets publish, which stay internal. | transcript L7 |
| D4 | Road geometry stays canonical in OSM — we contribute, never fork (revert/ban risk). | scope pivot |
| D5 | 3D buildings via **CityGML / 3D CityDB**; convert internal building → OSM polygon; web editor, no install. | transcript L13-19 |

---

## 3. Open questions to resolve this afternoon

**Q1 — Stable ID across OSM churn (LOCK THIS FIRST).**
Private metadata hangs off a way_id. OSM way_ids split/die on external geometry edits — split ways inherit stale attrs (already observed: 70% of QL.51 re-dated). Need an **internal stable feature-id** + a way_id↔stable-id map that re-syncs. Without it, private metadata orphans on every external edit. *Nothing else is safe until this is decided.*

**Q2 — Routing ↔ maptile sync lag.**
Routing immediate, maptile weekly, but leadership wants edits visible **on the map** fast. Which edits jump the queue? Define SLA per artifact + exception path.

**Q3 — Version pairing.**
data-ver + config-ver × 2 PBFs. How does the API guarantee routing v-N pairs with maptile v-N so navigation and display agree? Need a version-lock contract.

**Q4 — Changeset push authority.**
Who approves changeset → OSM vs hold-private — QA (RAP) or lead? Ties to D2/D3.

**Q5 — 3D/building editor scope.**
CityGML convert + web building editor = new tool. Own tool, or a tab in the MapOps one-page (Quân's model)? Also: layer registration — at zoom 15-16 the 3D layer must align with OSM base or renders blurry/doubled.

---

## 4. MapOps tool = 3 surfaces (build report on the pipeline it already needs)

1. **Task board** — claim way_id → edit → mark done.
2. **Pipeline / QA** — staging → changeset review (RAP) → publish gate.
3. **Report dashboard** — internal-capability numbers.

## 5. Numbers to report (capability proof)

**Headline 3:**
- **km/week edited** — per editor, per quốc lộ, vs scope-pivot target.
- **OSM revert rate + QA pass %** — the number that proves edits *stick*, not vanity.
- **Coverage growth** — national-road km with maxspeed/name/lanes over time (12.9% → curve).

**Secondary:** time-per-edit (budget input), % edits with street-view evidence, claimable backlog remaining, POI crawled/deduped/verified + confidence dist, **push ratio** (OSM vs private), **sync freshness** (routing-vs-maptile version drift in days).

---

*Ask of the room: lock Q1 (stable ID), agree Q2 SLA + Q3 version pairing. Q4/Q5 can follow.*
