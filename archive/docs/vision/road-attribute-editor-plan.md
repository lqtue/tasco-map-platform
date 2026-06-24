# Road-Attribute Editor — Product & Research Plan

> **Owner:** Tuệ (product lead) · **Updated:** 2026-06-22
> **Target:** maxspeed on most of the national + expressway network (~28,000 km) at **launch, early September 2026**.
>
> Productizes `traffic/lanes/` into TASCO's internal multi-source road-attribute editor. Ladders to
> [Enterprise Architecture](./enterprise-architecture.md) ("Editor Spatial DB Server") and the O3
> enrichment workstream. Extends the 2026-06-15 scope pivot (road-by-road, evidence-per-edit).

---

## 1. TL;DR

We are not "editing 28,000 km of road." We are **solving one estimation problem** — *what is the
speed limit on each stretch of road, and how sure are we?* — and then spending scarce editor-hours
only where the math says a human is needed. Framed that way, an early-September launch is feasible:
the busiest national roads are exactly the ones where the estimate is most confident and cheapest to
confirm.

This document opens with the **plain five-step flow** (§2), **what we're building and how it grows**
beyond maxspeed (§3), and **the team/roles it takes** (§4). The deeper half then states the
estimation problem as **one objective**, decomposes it into **eight sub-problems** (each with its
method, the research that backs it, and its status), and lays out the **phased plan** to ship it.

> **Launch constraint (drives everything below).** ~10 weeks to early September. **Purchased + CV-processed
> satellite cannot make that date** (procurement + processing lead time) → it moves to a post-launch
> accelerator. Satellite stays only as a **free visual basemap** for reading morphology by eye. The
> binding constraint at launch is **editor throughput, not data processing** — so every design choice
> below optimises *correct km confirmed per editor-hour*.

---

## 2. How it works — the simple flow

Strip the math and the system is **five steps in order**. The first four run by machine, before
anyone opens the tool; a person does only step 5, and only where step 4 says a person is needed.

1. **Guess from the road's shape.** Every stretch gets a *legal-default* speed from its morphology (expressway, divided rural, built-up…) via the Thông tư 38 rules. Free, instant, covers 100% of the network — but it's only the default, not a posted limit.
2. **Look for the real sign.** Pull street-view sign detections (Mapillary now; our own cameras/CV later) that override the default wherever a limit is actually posted.
3. **Clean and place each sign.** The same sign is seen many times with scattered GPS; collapse those into one point and work out which carriageway and direction it governs.
4. **Join it into a profile, and rate our confidence.** A road's speed holds over long *runs* and only jumps at *change-points* (a sign, a built-up boundary, a divided→single change). Build that step-profile and mark each run **confident / needs-a-look / no-data**.
5. **Human confirms with evidence, then it ships.** The editor works a ranked worklist, confirms the handful of uncertain change-points against the street-view photo, and the confirmed run is written back to OSM citing that evidence.

The whole point of steps 1–4 is to make step 5 small: a human *confirms a machine's suggestion
against a photo*, instead of reading 28,000 km of road by hand. Fig. 1 (§6) shows this as a
pipeline; everything after §4 is just *how each step is computed*.

---

## 3. What we're building, and how it grows

maxspeed is the **first attribute** on a general **road-attribute editor**, not a one-off. The same
five-step flow — *prior → detect → localize → chain → human-confirm* — works for any attribute that
is either **posted on a sign** or **readable from road shape**. So the platform grows along two axes,
**attributes** and **evidence sources**, reusing the same machine.

| Attribute | What estimates it | Evidence source(s) | When |
|---|---|---|---|
| **maxspeed** | TT38 morphology prior + posted sign | Mapillary signs · satellite morphology (basemap) | **Now — launch** |
| **No-overtaking (cấm vượt)** | posted sign | street-view CV | Next (same sign pipeline) |
| **Residential enter/exit (khu dân cư)** | posted sign → built-up default | street-view CV | Next |
| **Lane count** | road shape | satellite/aerial CV · OSM | Phase 2 (CV) |
| **Other prohibition signs** | posted sign | own CV | Phase 4 |
| **Signals / intersection attrs** | intersection geometry + signs | street-view + graph (intersection-based, hard) | Deferred |

The **evidence stack** also deepens under all of them over time:

> street-view *lookup* (read by eye) → **Mapillary CV signs** (now) → **satellite-morphology CV**
> (purchased imagery, post-launch) → **our own dashcam fleet + retrained CV** (owns both the evidence
> and the retraining loop).

Each new attribute is **a new detector + a new sheet column**, not a new tool — the chain model,
triage, editor sheet, evidence policy and write-back are shared. (Detection of signals and lanes
stays *deferred*; the lanes QA view already ships in `traffic/lanes/`.)

### 3.1 Beyond attributes: the QA-tool suite (an "Atlas" page)

Leadership flagged five public OSM tools to fold in — turn restrictions ([ahorn `/tr`](https://ahorn.lima-city.de/tr/)),
change-tracking ([WhoDidIt](https://simon04.dev.openstreetmap.org/whodidit/)), [Bolt Atlas](https://atlas.bolt.eu/),
truck/max-height ([osm-maxheight-map](https://github.com/lbarrosop/osm-maxheight-map)) and parking
([tilda Parkraum](https://tilda-geo.de/regionen/parkraum)). The strategic read: **don't embed five
sites — give the editor a tool suite, like Bolt's Atlas Map Tools.** Atlas isn't five apps; it's
**one map shell + one data substrate, each tool a lens**. We already have both halves in embryo —
the shell is `traffic/lanes/`, the substrate is the planned Editor Spatial DB Server. So the editor
becomes a **module registry**: one map, one staged-edit worklist, one evidence policy; each
capability plugs in as a module.

Two kinds of module, both reusing the shell:

- **Per-segment attributes** — maxspeed, lanes, signs. These are *sheet columns* (the §3 model above).
- **Standalone QA tools** — turn restrictions, max-height/weight/width, parking, change-tracking.
  These aren't per-segment columns; each is a geometry/validation/feed view of its own, but it still
  shares the map, worklist and evidence links.

They split across **two data tiers**, matched to our actual inputs:

| Tier | What it is | Our input | Modules it serves |
|---|---|---|---|
| **A — Overpass-live** *(now, zero infra; lanes already does this)* | on-demand bbox/relation query in the browser | live OSM | maxspeed/lanes/signs · **turn restrictions** (`rel[restriction]` + validation) · **max-height** (tag styling + `around:0` bridge-intersection check) |
| **B — Editor Spatial DB** *(= the planned server; osm2pgsql from the VN PBF we already download → PostGIS, temporal)* | local PBF · Mapillary parquet · Open Buildings | **change-tracking** (diff-feed) · **parking** (osm2pgsql + capacity/subtractive model) · nationwide progress · write-back |

The non-obvious priority: **change-tracking is the highest-leverage tool.** The scope pivot puts
20–30 paid-per-km part-time editors on the map with **evidence-per-edit mandatory or accounts get
banned**. A "what changed in this corridor / by which editor / with what evidence" feed is direct
operational QA — and it's the exact use-case the temporal Editor DB exists for, so it *pays for*
Tier B rather than just consuming it. WhoDidIt's whole MySQL+diff stack collapses into "ingest the
diffs we already download"; cheaper interim substitutes (OSM `changesets` API, Overpass `adiff`,
ohsome) give the same area-feed with no backend. **Bolt Atlas itself is not integratable** — its
value rests on Bolt's private GPS traces — but its *checks* (oneway/access consistency, route
plausibility) are reproducible later on our own Mapillary GPS.

---

## 4. Team & operating model

This is **not a solo effort, and not only an editing team** — it spans data, ML, tooling, operations
and review. The operating loop is **machine proposes → MapOps confirms with evidence → Engineering
publishes → Product monitors**, and each arm needs an owner. Listed as *roles*, some filled today,
some to staff as the program grows:

| Role | Owns | In the flow | When |
|---|---|---|---|
| **Product / program lead** | objective, scope, evidence policy, priorities | all | now |
| **Geospatial data engineer** | OSM/Mapillary/imagery ingestion, TT38 prior, suggestion store, dashboards | steps 1–4 | now |
| **Computer-vision engineer** | sign/lane detectors, denoise+localize, own-CV retraining | steps 2–3 | **to staff** |
| **ML / inference engineer** | chain model (SP5), confidence + triage thresholds (SP6) | step 4 | now → soon |
| **Tooling / frontend engineer** | the editor (`traffic/lanes/`): sheet, map, profile, write-back | step 5 | now |
| **MapOps editors** | confirm suggestions against evidence, flag conflicts | step 5 | now (core) → **scale** |
| **MapOps lead / QA** | SOP, training, the revert/review gate, per-editor changeset attribution | step 5 | now |
| **Backend / platform engineer** | Editor Spatial DB Server, OSM write-back + sync | step 5 (Phase 3) | later |

**How it scales.** A small core hand-edits and **screen-records to build the SOP**; the SOP trains
**paid-per-km part-time editors**; and those labelled confirmations become training data for an
**AI-assisted auto-edit** path (always behind mandatory human review). Headcount, pay-per-km rate and
the QA gate are product-owner decisions (§13). The **computer-vision engineer is the key to-staff
role**: until it's filled the program runs on Mapillary's (European-trained, partial-VN) detector —
which is exactly why own-CV is a post-launch accelerator, not a launch dependency.

---

> **The method, in depth (§5–§11).** The rest of this document is *how each step above is computed* —
> the estimation objective, the eight sub-problems, the chain model, and where satellite fits.
> Roadmap, decisions and sizing resume at §12.

## 5. The big problem, in one objective

We want to maximise the **correct, traffic-weighted kilometres** of maxspeed we can confirm within a
fixed editor-hour budget before the launch date:

```
maximise   Σ_runs  km(run) · 1[ v̂(run) = v_true(run) ] · w_traffic(run)
subject to Σ editor-hours ≤ budget,   deadline = early September
```

A *run* is a maximal stretch of road over which the limit is constant (definition in §7). To pick
`v̂(run)` we need a per-run estimate **with calibrated confidence** — so the inner problem is
Bayesian estimation of the limit `v` on each segment `s`:

```
P(v_s | E)  ∝   P(v_s | morphology_s)        ← PRIOR     : Thông tư 38 legal default
              × Π_k P(e_k | v_s)              ← EVIDENCE  : independent observations (street-view sign…)
              × Π   P(v_s | v_neighbour)      ← COUPLING  : speed is spatially autocorrelated
```

Everything else in this plan is **how we compute each factor of that product, and how we turn the
posterior into editor actions.** The two halves — *estimate the posterior* and *spend editor-hours
optimally given the posterior* — are the two columns of the decomposition in §7.

> **One hygiene rule on the EVIDENCE term.** maxspeed.nl / MaxBit / most reference layers are
> *derived from OSM*, so they are **not** independent likelihood terms — counting them inflates
> confidence. Independent evidence = street-view signs, satellite morphology, field survey. Reference
> layers are glance-only corroboration (also a licensing line — §13).

---

## 6. System overview

The estimation runs **offline in pipelines**; the browser only renders suggestions and stages edits.

<figure>
<svg viewBox="0 0 860 300" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
<rect x="8" y="70" width="150" height="160" fill="#ffffff" stroke="#cbd5e1"/>
<rect x="8" y="70" width="150" height="24" fill="#1d4ed8"/>
<text x="83" y="87" text-anchor="middle" fill="#ffffff" font-size="11" font-weight="bold">SOURCES</text>
<text x="18" y="114" font-size="10.5" fill="#1f2933">OSM (base + target)</text>
<text x="18" y="134" font-size="10.5" fill="#1f2933">Mapillary signs</text>
<text x="18" y="154" font-size="10.5" fill="#1f2933">Satellite basemap</text>
<text x="18" y="174" font-size="10.5" fill="#1f2933">TT38 legal rules</text>
<text x="18" y="194" font-size="10.5" fill="#1f2933">Open Buildings</text>
<rect x="180" y="70" width="172" height="160" fill="#ffffff" stroke="#cbd5e1"/>
<rect x="180" y="70" width="172" height="24" fill="#1d4ed8"/>
<text x="266" y="87" text-anchor="middle" fill="#ffffff" font-size="11" font-weight="bold">OFFLINE INFERENCE</text>
<text x="190" y="114" font-size="10.5" fill="#1f2933">SP2 detect signs</text>
<text x="190" y="134" font-size="10.5" fill="#1f2933">SP3 denoise + localize</text>
<text x="190" y="154" font-size="10.5" fill="#1f2933">SP4 assign to segment</text>
<text x="190" y="174" font-size="10.5" fill="#1f2933">SP5 chain MAP (runs)</text>
<text x="190" y="194" font-size="10.5" fill="#1f2933">SP6 confidence</text>
<rect x="374" y="70" width="150" height="160" fill="#ffffff" stroke="#cbd5e1"/>
<rect x="374" y="70" width="150" height="24" fill="#1d4ed8"/>
<text x="449" y="87" text-anchor="middle" fill="#ffffff" font-size="11" font-weight="bold">SUGGESTION STORE</text>
<text x="384" y="114" font-size="10.5" fill="#1f2933">parquet, per run:</text>
<text x="384" y="134" font-size="10.5" fill="#1f2933">value · P(v)</text>
<text x="384" y="154" font-size="10.5" fill="#1f2933">change-points</text>
<text x="384" y="174" font-size="10.5" fill="#1f2933">evidence_url</text>
<rect x="546" y="70" width="150" height="160" fill="#ffffff" stroke="#cbd5e1"/>
<rect x="546" y="70" width="150" height="24" fill="#1d4ed8"/>
<text x="621" y="87" text-anchor="middle" fill="#ffffff" font-size="11" font-weight="bold">EDITOR TOOL</text>
<text x="556" y="114" font-size="10.5" fill="#1f2933">sheet + map</text>
<text x="556" y="134" font-size="10.5" fill="#1f2933">speed-profile =</text>
<text x="556" y="154" font-size="10.5" fill="#1f2933">chain MAP</text>
<text x="556" y="174" font-size="10.5" fill="#1f2933">confirm a run</text>
<rect x="718" y="70" width="134" height="160" fill="#ffffff" stroke="#cbd5e1"/>
<rect x="718" y="70" width="134" height="24" fill="#1d4ed8"/>
<text x="785" y="87" text-anchor="middle" fill="#ffffff" font-size="11" font-weight="bold">OUTPUT</text>
<text x="728" y="114" font-size="10.5" fill="#1f2933">staged CSV →</text>
<text x="728" y="134" font-size="10.5" fill="#1f2933">iD / JOSM (now)</text>
<text x="728" y="164" font-size="10.5" fill="#1f2933">Editor Spatial</text>
<text x="728" y="184" font-size="10.5" fill="#1f2933">DB ↔ OSM (later)</text>
<line x1="160" y1="150" x2="174" y2="150" stroke="#6b7280" stroke-width="2"/>
<polygon points="174,146 182,150 174,154" fill="#6b7280"/>
<line x1="354" y1="150" x2="368" y2="150" stroke="#6b7280" stroke-width="2"/>
<polygon points="368,146 376,150 368,154" fill="#6b7280"/>
<line x1="526" y1="150" x2="540" y2="150" stroke="#6b7280" stroke-width="2"/>
<polygon points="540,146 548,150 540,154" fill="#6b7280"/>
<line x1="698" y1="150" x2="712" y2="150" stroke="#6b7280" stroke-width="2"/>
<polygon points="712,146 720,150 712,154" fill="#6b7280"/>
<line x1="785" y1="246" x2="83" y2="246" stroke="#9bb4d6" stroke-width="1.5" stroke-dasharray="5,4"/>
<line x1="785" y1="230" x2="785" y2="246" stroke="#9bb4d6" stroke-width="1.5"/>
<line x1="83" y1="246" x2="83" y2="230" stroke="#9bb4d6" stroke-width="1.5"/>
<polygon points="83,230 79,238 87,238" fill="#9bb4d6"/>
<text x="434" y="262" text-anchor="middle" font-size="10" fill="#6b7280" font-style="italic">confirmed edits re-enter OSM → next data cycle</text>
</svg>
<figcaption><b>Fig. 1 — System data-flow.</b> Detection and inference are offline; the editor consumes a precomputed suggestion store and stages edits.</figcaption>
</figure>

---

## 7. Decomposition: one objective → eight sub-problems

Each factor of the posterior, plus the "spend editor-hours well" half, becomes a sub-problem we can
build and test in isolation.

<figure>
<svg viewBox="0 0 860 430" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
<rect x="230" y="12" width="400" height="40" fill="#1d4ed8"/>
<text x="430" y="30" text-anchor="middle" fill="#ffffff" font-size="12" font-weight="bold">OBJECTIVE — max correct, traffic-weighted km / editor-hour</text>
<text x="430" y="45" text-anchor="middle" fill="#dbe5fb" font-size="10">inner problem: posterior  P(v | E) ∝ prior × evidence × coupling</text>
<line x1="430" y1="52" x2="430" y2="70" stroke="#9bb4d6" stroke-width="1.5"/>
<line x1="150" y1="70" x2="710" y2="70" stroke="#9bb4d6" stroke-width="1.5"/>
<line x1="150" y1="70" x2="150" y2="86" stroke="#9bb4d6" stroke-width="1.5"/>
<line x1="400" y1="70" x2="400" y2="86" stroke="#9bb4d6" stroke-width="1.5"/>
<line x1="710" y1="70" x2="710" y2="86" stroke="#9bb4d6" stroke-width="1.5"/>
<rect x="60" y="86" width="180" height="26" fill="#eef3fc" stroke="#9bb4d6"/>
<text x="150" y="104" text-anchor="middle" fill="#1d4ed8" font-size="11" font-weight="bold">PRIOR</text>
<rect x="300" y="86" width="200" height="26" fill="#eef3fc" stroke="#9bb4d6"/>
<text x="400" y="104" text-anchor="middle" fill="#1d4ed8" font-size="11" font-weight="bold">EVIDENCE</text>
<rect x="610" y="86" width="200" height="26" fill="#eef3fc" stroke="#9bb4d6"/>
<text x="710" y="104" text-anchor="middle" fill="#1d4ed8" font-size="11" font-weight="bold">INFERENCE + ALLOCATION</text>
<rect x="60" y="130" width="180" height="46" fill="#ffffff" stroke="#cbd5e1"/>
<text x="68" y="148" font-size="10.5" font-weight="bold" fill="#1f2933">SP1 Prior from morphology</text>
<text x="68" y="166" font-size="10" fill="#6b7280">TT38 rules → legal default</text>
<rect x="300" y="130" width="200" height="46" fill="#ffffff" stroke="#cbd5e1"/>
<text x="308" y="148" font-size="10.5" font-weight="bold" fill="#1f2933">SP2 Sign detection</text>
<text x="308" y="166" font-size="10" fill="#6b7280">imagery → sign value + position</text>
<rect x="300" y="184" width="200" height="46" fill="#ffffff" stroke="#cbd5e1"/>
<text x="308" y="202" font-size="10.5" font-weight="bold" fill="#1f2933">SP3 Denoise + localize</text>
<text x="308" y="220" font-size="10" fill="#6b7280">many detections → 1 point + pose</text>
<rect x="300" y="238" width="200" height="46" fill="#ffffff" stroke="#cbd5e1"/>
<text x="308" y="256" font-size="10.5" font-weight="bold" fill="#1f2933">SP4 Assign to segment</text>
<text x="308" y="274" font-size="10" fill="#6b7280">heading + HMM map-match</text>
<rect x="610" y="130" width="200" height="46" fill="#ffffff" stroke="#cbd5e1"/>
<text x="618" y="148" font-size="10.5" font-weight="bold" fill="#1f2933">SP5 Chain MAP</text>
<text x="618" y="166" font-size="10" fill="#6b7280">runs + change-points (Viterbi)</text>
<rect x="610" y="184" width="200" height="46" fill="#ffffff" stroke="#cbd5e1"/>
<text x="618" y="202" font-size="10.5" font-weight="bold" fill="#1f2933">SP6 Confidence + triage</text>
<text x="618" y="220" font-size="10" fill="#6b7280">auto-accept / human / defer</text>
<rect x="610" y="238" width="200" height="46" fill="#ffffff" stroke="#cbd5e1"/>
<text x="618" y="256" font-size="10.5" font-weight="bold" fill="#1f2933">SP7 Prioritization</text>
<text x="618" y="274" font-size="10" fill="#6b7280">rank by traffic × uncertainty</text>
<line x1="150" y1="112" x2="150" y2="130" stroke="#cbd5e1" stroke-width="1.5"/>
<line x1="400" y1="112" x2="400" y2="130" stroke="#cbd5e1" stroke-width="1.5"/>
<line x1="710" y1="112" x2="710" y2="130" stroke="#cbd5e1" stroke-width="1.5"/>
<rect x="300" y="330" width="260" height="46" fill="#fff7ed" stroke="#d6a86a"/>
<text x="430" y="348" text-anchor="middle" font-size="10.5" font-weight="bold" fill="#b45309">SP8 Apply + write-back</text>
<text x="430" y="366" text-anchor="middle" font-size="10" fill="#92702a">confirmed run → OSM edit w/ evidence</text>
<line x1="430" y1="284" x2="430" y2="330" stroke="#d6a86a" stroke-width="1.5" stroke-dasharray="4,3"/>
<text x="430" y="402" text-anchor="middle" font-size="10" fill="#6b7280" font-style="italic">SP1–SP7 feed the editor; SP8 ships the human-confirmed result back to OSM</text>
</svg>
<figcaption><b>Fig. 2 — Problem decomposition.</b> The objective splits into the three posterior factors (prior / evidence / coupling) plus the allocation half; eight sub-problems, each independently buildable.</figcaption>
</figure>

### The sub-problem ledger

| # | Sub-problem | Input → Output | Method | Research / precedent | Launch-critical | Status |
|---|---|---|---|---|---|---|
| SP1 | Prior from morphology | morphology tags → legal default `v`, `P(v\|m)` | TT38 decision tree (rules) | Guth et al. 2020; TT38 38/2024 | ✅ | **Done** — `legalUrban/Rural` on each `SheetRow`; subset morphology-% TBD |
| SP2 | Sign detection | street imagery → sign value + position | CNN detector (Mapillary now; own CV later) | Ajmar 2019; RoadTagger 2020; Tusher 2024 (domain gap) | ✅ (Mapillary) | Sidecar live; own CV post-launch |
| SP3 | Denoise + localize | many noisy detections → 1 point + pose | context-aware confidence clustering | Kango 2024; Yang & Ai 2018 | ✅ | **Not built** (new — §9) |
| SP4 | Assign to segment | sign point + heading → `way_id`, direction | heading-augmented HMM map-match + side-of-road + `pairId` | Kango 2024; Newson & Krumm 2009; Liu 2020 | ✅ | Heuristic (`pairId`) exists; HMM TBD |
| SP5 | Chain MAP | per-segment prior + evidence → runs + change-points | linear-chain CRF/HMM, Viterbi (graph reduction) | RoadTagger 2020; Jepsen 2019/2022 | ✅ (heuristic) | Heuristic chain TBD; speed-profile UI done |
| SP6 | Confidence + triage | posterior → auto-accept / human / defer | learned confidence + thresholds | Kango 2024 (auto-reviewer) | ✅ | Threshold policy TBD |
| SP7 | Prioritization | runs → ranked worklist | value-weighted info gain (traffic × uncertainty) | heuristic; Mapillary-density proxy | ✅ | TBD |
| SP8 | Apply + write-back | confirmed run → OSM edit w/ evidence | staged CSV → iD/JOSM now; Editor Spatial DB later | enterprise-architecture.md; Kango 2024 | ❌ (export now) | Export done; backend Phase 3 |

---

## 8. The chain model, made visual (SP5)

A road is **not** N independent segments — its attributes are **spatially autocorrelated** (the
empirical premise of RoadTagger, He et al. 2020, and of Jepsen et al.'s OSM speed-limit work). The
limit holds over long homogeneous **runs** and jumps only at **change-points**: a posted sign, a
built-up enter/exit sign, a divided→single morphology change, a major junction. The estimate is the
**Viterbi path** along the road; the editor's job collapses from "label thousands of segments" to
"**confirm the handful of change-points**."

<figure>
<svg viewBox="0 0 860 300" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
<line x1="60" y1="40" x2="60" y2="240" stroke="#cbd5e1" stroke-width="1"/>
<line x1="60" y1="240" x2="820" y2="240" stroke="#cbd5e1" stroke-width="1"/>
<text x="30" y="244" font-size="9" fill="#6b7280">50</text>
<text x="30" y="194" font-size="9" fill="#6b7280">80</text>
<text x="30" y="164" font-size="9" fill="#6b7280">90</text>
<text x="24" y="104" font-size="9" fill="#6b7280">120</text>
<line x1="60" y1="190" x2="820" y2="190" stroke="#eef0f4" stroke-width="1"/>
<line x1="60" y1="160" x2="820" y2="160" stroke="#eef0f4" stroke-width="1"/>
<line x1="60" y1="100" x2="820" y2="100" stroke="#eef0f4" stroke-width="1"/>
<text x="14" y="150" font-size="10" fill="#6b7280" transform="rotate(-90 14 150)" text-anchor="middle">maxspeed (km/h)</text>
<polyline points="60,160 240,160 240,240 380,240 380,160 560,160 560,190 680,190 680,100 820,100" fill="none" stroke="#1d4ed8" stroke-width="2.5"/>
<line x1="240" y1="40" x2="240" y2="240" stroke="#dc2626" stroke-width="1" stroke-dasharray="4,3"/>
<line x1="380" y1="40" x2="380" y2="240" stroke="#dc2626" stroke-width="1" stroke-dasharray="4,3"/>
<line x1="560" y1="40" x2="560" y2="240" stroke="#b45309" stroke-width="1" stroke-dasharray="4,3"/>
<line x1="680" y1="40" x2="680" y2="240" stroke="#b45309" stroke-width="1" stroke-dasharray="4,3"/>
<polygon points="240,40 234,52 246,52" fill="#dc2626"/>
<polygon points="380,40 374,52 386,52" fill="#dc2626"/>
<polygon points="560,40 554,52 566,52" fill="#b45309"/>
<polygon points="680,40 674,52 686,52" fill="#b45309"/>
<text x="240" y="36" text-anchor="middle" font-size="8.5" fill="#dc2626">sign</text>
<text x="380" y="36" text-anchor="middle" font-size="8.5" fill="#dc2626">sign</text>
<text x="560" y="36" text-anchor="middle" font-size="8.5" fill="#b45309">morph.</text>
<text x="680" y="36" text-anchor="middle" font-size="8.5" fill="#b45309">expwy</text>
<text x="150" y="155" text-anchor="middle" font-size="9" fill="#475569">run A</text>
<text x="310" y="235" text-anchor="middle" font-size="9" fill="#475569">run B</text>
<text x="470" y="155" text-anchor="middle" font-size="9" fill="#475569">run C</text>
<text x="620" y="185" text-anchor="middle" font-size="9" fill="#475569">run D</text>
<text x="750" y="95" text-anchor="middle" font-size="9" fill="#475569">run E</text>
<rect x="120" y="258" width="14" height="3" fill="#1d4ed8"/>
<text x="140" y="263" font-size="9.5" fill="#6b7280">MAP estimate (the speed-profile chart in the tool)</text>
<line x1="430" y1="259" x2="444" y2="259" stroke="#dc2626" stroke-width="1" stroke-dasharray="4,3"/>
<text x="450" y="263" font-size="9.5" fill="#6b7280">change-point (street-view evidence required)</text>
<line x1="120" y1="277" x2="134" y2="277" stroke="#b45309" stroke-width="1" stroke-dasharray="4,3"/>
<text x="140" y="281" font-size="9.5" fill="#6b7280">change-point (morphology — readable from satellite)</text>
</svg>
<figcaption><b>Fig. 3 — Speed as a chain.</b> Confirm the change-points, auto-fill the runs between them. Each run's changeset cites the boundary sign — which is also how the law works (a sign governs until the next sign), so this defuses the revert/ban risk and collapses the work.</figcaption>
</figure>

> **Model note.** A linear-chain CRF / HMM is the practical single-road *reduction* of the graph
> propagation in RoadTagger/Jepsen (a route is a degenerate graph). Ship the **heuristic chain**
> first (propagate confident signs, break at change-signs / morphology changes, else legal default);
> upgrade to a full CRF/graph model only if accuracy measurably needs it.

---

## 9. The new piece: denoise & localize, then assign (SP3 → SP4)

The hardest, least-built link. The same sign is detected many times with scattered geolocation
error, so we must **cluster repeated detections into one representative point + pose before
assignment** — confidence-weighted, context-aware on sign pose + detection angle + vehicle heading
(Kango et al. 2024 beat fixed-distance clustering, esp. near intersections). Then map-match with
**vehicle heading** (Mapillary `compass_angle`) + side-of-road + the existing `pairId` carriageway
pairing — the classic HMM map-match (Newson & Krumm 2009) augmented with heading, which is what
resolves carriageway / U-turn ambiguity (it lifted hard-case accuracy 26%→84% in Kango 2024).
maxspeed is **way-based** (project to the nearest point on the matched way) — the tractable case;
intersection-based signs (signals) are the hard, deferred class.

**Pipeline output the tool consumes (one row per run):**
`[way_id, run_id, value, P(v), is_change_point, evidence_url, n_detections, cluster_spread, pose_angle]`
— the last three are the strongest auto-accept-confidence features.

---

## 10. Spending editor-hours well (SP6 → SP7)

The posterior tells us **where a human is actually needed**. Three outcomes:

<figure>
<svg viewBox="0 0 860 230" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
<rect x="20" y="80" width="190" height="70" fill="#eef3fc" stroke="#9bb4d6"/>
<text x="115" y="108" text-anchor="middle" font-size="11" font-weight="bold" fill="#1d4ed8">candidate runs</text>
<text x="115" y="126" text-anchor="middle" font-size="9.5" fill="#475569">ranked by traffic × uncertainty</text>
<line x1="210" y1="115" x2="270" y2="60" stroke="#6b7280" stroke-width="1.5"/>
<line x1="210" y1="115" x2="270" y2="115" stroke="#6b7280" stroke-width="1.5"/>
<line x1="210" y1="115" x2="270" y2="170" stroke="#6b7280" stroke-width="1.5"/>
<polygon points="270,60 262,60 268,67" fill="#6b7280"/>
<polygon points="270,115 263,111 263,119" fill="#6b7280"/>
<polygon points="270,170 268,163 262,170" fill="#6b7280"/>
<rect x="272" y="38" width="300" height="46" fill="#ecfdf3" stroke="#5cab7d"/>
<text x="284" y="58" font-size="10.5" font-weight="bold" fill="#15803d">AUTO-ACCEPT   posterior &gt; τ_high</text>
<text x="284" y="76" font-size="9.5" fill="#3f7a52">sharp prior + corroborating sign + neighbour agree</text>
<rect x="272" y="92" width="300" height="46" fill="#fff7ed" stroke="#d6a86a"/>
<text x="284" y="112" font-size="10.5" font-weight="bold" fill="#b45309">HUMAN REVIEW   flat / conflicting</text>
<text x="284" y="130" font-size="9.5" fill="#92702a">the change-points + ambiguous cases — the editor queue</text>
<rect x="272" y="146" width="300" height="46" fill="#f3f4f6" stroke="#cbd5e1"/>
<text x="284" y="166" font-size="10.5" font-weight="bold" fill="#6b7280">DEFER   low traffic + no data</text>
<text x="284" y="184" font-size="9.5" fill="#6b7280">long tail — post-launch / satellite fills later</text>
<rect x="600" y="38" width="240" height="154" fill="#ffffff" stroke="#cbd5e1"/>
<text x="612" y="58" font-size="10" font-weight="bold" fill="#1f2933">Reality check (Kango 2024):</text>
<text x="612" y="78" font-size="9.5" fill="#475569">at 99% precision, auto-accept</text>
<text x="612" y="94" font-size="9.5" fill="#475569">recall ≈ 50% (stop) / 20% (light).</text>
<text x="612" y="116" font-size="9.5" fill="#475569">maxspeed (way-based) beats that,</text>
<text x="612" y="132" font-size="9.5" fill="#475569">but the human queue is the</text>
<text x="612" y="148" font-size="9.5" fill="#475569">bottleneck — size September on it,</text>
<text x="612" y="164" font-size="9.5" fill="#475569">not on auto-coverage.</text>
</svg>
<figcaption><b>Fig. 4 — Triage.</b> Auto-accept the confident, route the ambiguous to humans, defer the long tail. Editor-hours go only to the middle band.</figcaption>
</figure>

**Why the national roads are the low-hanging fruit** — every posterior term favours them:

| Term | On the big roads | Effect |
|---|---|---|
| Prior `P(v\|morphology)` | morphology uniform + well-tagged (expressway→120, divided rural→90) | sharp prior, low entropy |
| Coupling | long consistent runs, few change-points / 100 km | one observation propagates over many km |
| Evidence cost | driven/captured most → dense Mapillary | cheap to confirm |
| Value | highest traffic | each correct edit worth the most |

The same signal — **Mapillary density** — is both the value proxy and the evidence-cost proxy, and
they coincide on exactly the roads we care about. *Caveat:* density is a **biased** traffic proxy
(contributor behaviour, not AADT; skews to populated areas — Jepsen et al. 2022). Fine for ranking,
not ground-truth volume.

---

## 11. Two-track evidence (where satellite fits)

TT38 keys speed on **morphology, not highway class**, which splits the evidence cleanly:

| Track | Answers | Source | At launch |
|---|---|---|---|
| **Satellite** | morphology → the **legal-default prior** (đường đôi/đơn, lanes, built-up) | free basemap by eye now; purchased + CV later | **free basemap only** |
| **Street-view** | the **posted sign** that overrides the default (the change-points) | Mapillary now → own dashcam/CV | **primary evidence** |

> **Compliance line (do not blur).** Satellite morphology → legal-default maxspeed is legitimate,
> scalable evidence. A *posted* (non-default) limit still needs the sign. Crossing this gets
> changesets reverted and accounts banned.

---

## 12. Roadmap

<figure>
<svg viewBox="0 0 860 260" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
<line x1="40" y1="40" x2="820" y2="40" stroke="#cbd5e1" stroke-width="1"/>
<text x="120" y="28" text-anchor="middle" font-size="9.5" fill="#6b7280">Jun</text>
<text x="300" y="28" text-anchor="middle" font-size="9.5" fill="#6b7280">Jul</text>
<text x="470" y="28" text-anchor="middle" font-size="9.5" fill="#6b7280">Aug</text>
<text x="600" y="28" text-anchor="middle" font-size="9.5" fill="#6b7280">Sep</text>
<text x="740" y="28" text-anchor="middle" font-size="9.5" fill="#6b7280">Q4+</text>
<line x1="600" y1="34" x2="600" y2="230" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="5,4"/>
<text x="600" y="246" text-anchor="middle" font-size="10" font-weight="bold" fill="#dc2626">LAUNCH (early Sep)</text>
<rect x="40" y="56" width="80" height="26" fill="#d1fae5" stroke="#5cab7d"/>
<text x="80" y="73" text-anchor="middle" font-size="9.5" fill="#15803d" font-weight="bold">Phase 0 ✓</text>
<text x="124" y="73" font-size="9.5" fill="#475569">MVP: sheet, edits→CSV, legal defaults, speed-profile</text>
<rect x="120" y="92" width="480" height="26" fill="#dbe5fb" stroke="#9bb4d6"/>
<text x="360" y="109" text-anchor="middle" font-size="9.5" fill="#1d4ed8" font-weight="bold">Phase 1 — to launch</text>
<text x="120" y="134" font-size="9.5" fill="#475569">bulk fill-run · sat basemap · sign+change-point column · heuristic chain · SOP pilot · onboard editors</text>
<rect x="600" y="150" width="220" height="26" fill="#ede9fe" stroke="#a78bca"/>
<text x="710" y="167" text-anchor="middle" font-size="9.5" fill="#6d28d9" font-weight="bold">Phase 2 — purchased + CV satellite</text>
<text x="600" y="192" font-size="9.5" fill="#475569">auto-morphology · own CV (other signs + lanes) · multi-source conflict flagging</text>
<rect x="660" y="206" width="160" height="22" fill="#fae8e8" stroke="#d6a0a0"/>
<text x="740" y="221" text-anchor="middle" font-size="9" fill="#b45309" font-weight="bold">Phase 3 — Editor Spatial DB ↔ OSM</text>
<text x="40" y="221" font-size="9" fill="#6b7280" font-style="italic">Phase 4 (later): signals, lanes, more signs; AI-assisted auto-edit + mandatory human review</text>
</svg>
<figcaption><b>Fig. 5 — Roadmap.</b> Phase 1 is the only thing on the launch critical path; purchased satellite and the write-back backend are deliberately post-launch.</figcaption>
</figure>

- **Phase 0 — done.** Sheet, inline editing, staged edits → CSV, legal defaults, completeness, speed profile, map.
- **Phase 1 — to launch.** *Tooling:* bulk "fill whole run/road" action; free satellite basemap; Mapillary sign-suggestion + change-point column; enforce the evidence policy (§13). *Method:* ship the heuristic chain (SP5) + denoise/assign (SP3/SP4) → per-run confidence. *Ops:* measure km/editor/day on a 1–2 road SOP pilot; clear **all expressways** first (small km, near-100% fast win), then national highways easy→hard; onboard editors. *Tracking:* daily ranked-road dashboard (km done vs official) + **revert-rate** watch.
- **Phase 2 — post-launch.** Purchased + CV satellite auto-derives morphology; own CV for other signs + lanes; full multi-source aggregation + conflict flagging. *Tool suite (§3.1):* refactor the editor into a module-registry shell and add the two zero-infra Tier-A modules — **turn restrictions** and **max-height** (pure Overpass).
- **Phase 3 — backend.** Editor Spatial DB Server (local PBF / Postgres+PostGIS) syncing with OSM; write-back with evidence + per-editor changeset attribution + QA queue. *Tool suite:* this tier unlocks the **change-tracking** module (editor-team QA, §3.1) and, after, **parking** (osm2pgsql + capacity model).
- **Phase 4 — scope.** Signals, lanes, more prohibition signs; AI-assisted auto-edit with mandatory human review.

---

## 13. Decisions the product owner owns

1. **Evidence policy (sets the speed ceiling).** Recommended **hybrid**: posted (non-default) limits require street-view evidence; legal defaults from visible morphology are tagged `source=survey/imagery` at human pace through editor accounts (not a bot import). Pure street-view-only is safe but coverage- and throughput-limited by Mapillary gaps.
2. **Imagery source & budget** — internal tile server vs commercial sub-meter; how much, where (coverage planner gives the buy-envelope). Drives lane-count feasibility. **Start procurement in parallel now** so it lands post-launch.
3. **Build vs buy CV** — own model (owns evidence + retraining loop) vs vendor.
4. **Write-back timing** — how long to stay export-first before funding the Editor Spatial DB.
5. **Editor ops** — headcount, pay-per-km rate, QA gate.

---

## 14. Throughput sizing (do this first)

Run `morphology_coverage.py` on the **national + expressway subset only**. The % carrying morphology
tags = the share auto-fillable from the prior (cheap bulk); the rest needs an editor to read
morphology off the free basemap. Then:

```
editor-days needed ≈ (28,000 km − auto-filled km) ÷ (editors × km/day)
```

Fill `km/day` from the SOP pilot (unmeasured; headcount/rates TBD). Because the method verifies
**runs, not segments**, `km/day` should be far higher than naïve per-segment editing — that gap is
the whole feasibility argument. **But don't over-size on auto-fill:** even production conflation holds
99% precision only at ~50%/20% recall (Kango 2024); the auto-accept path clears a *fraction*, the
rest is human. Size September on the **human queue**.

---

## 15. Metrics & risks

**Metrics.** Coverage % of the ~28k km subset — measure the baseline **on that subset** (via
`route_coverage.py` / `name_maxspeed_crosstab.py`), **not** the repo's 12.9% figure (that is over
*all* tertiary+, 133,771 km — wrong denominator here) · km/editor/day · time-per-run · suggestion-accept
rate · **revert rate (the quality gate)** · cost/km · traffic-weighted coverage.

**Risks.** Licensing contamination (Waze/Google) · evidence-less bulk edits → bans · Mapillary VN
gaps (mitigated: big roads densest; satellite fills the prior) · **Mapillary sparsity ⇒ noisier
localization than a controlled fleet** — clustering quality degrades with few traversals, so the
Kango 2024 blueprint pays off fully only with our own dashcam fleet · **ML speed-limit models don't
transfer across regions** — Jepsen et al. 2022 report cross-network accuracy collapsing to ~⅓, why we
lean on legal prior + local evidence over a foreign-trained model · over-trust in a flat posterior
(mitigated by triage) · backend conflict-resolution complexity (Phase 3).

---

## 16. Immediate next actions

1. **Run the morphology sizing** on the national + expressway subset → fixes the throughput target.
2. **Build the bulk "fill run to legal default" action + free satellite basemap** in the tool (SP1 → editor).
3. **Build SP3/SP4** (denoise + localize + heading-assign) and **SP5** heuristic chain → emit the per-run suggestion rows.
4. **Run the SOP pilot** (1–2 roads) to measure km/day and lock the evidence policy.
5. **Start satellite procurement in parallel** for the post-launch accelerator.

---

## References
- He, S., Bastani, F., Jagwani, S., et al. (2020). RoadTagger: Robust road attribute inference with graph neural networks. *AAAI, 34*(07), 10965–10972. https://doi.org/10.1609/aaai.v34i07.6730
- Jepsen, T. S., Jensen, C. S., & Nielsen, T. D. (2019). Graph convolutional networks for road networks. *ACM SIGSPATIAL*, 460–463. https://doi.org/10.1145/3347146.3359094
- Jepsen, T. S., Jensen, C. S., & Nielsen, T. D. (2022). Relational fusion networks: Graph convolutional networks for road networks. *IEEE T-ITS, 23*(1), 418–429. https://doi.org/10.1109/tits.2020.3011799
- Kango, V., Eraqi, H. M., & Moustafa, M. (2024). *High precision map conflation of fleet sourced traffic signs.* Amazon. (context-aware clustering + heading-augmented HMM map-matching + auto-reviewer; 99.5% precision auto-ingest.)
- Newson, P., & Krumm, J. (2009). Hidden Markov map matching through noise and sparseness. *ACM SIGSPATIAL*, 336–343.
- Guth, J., Wursthorn, S., & Keller, S. (2020). Multi-parameter estimation of average speed in road networks using fuzzy control. *ISPRS IJGI, 9*(1), 55. https://doi.org/10.3390/ijgi9010055
- Yang, W., Ai, T., & Lu, W. (2018). A method for extracting road boundary information from crowdsourcing vehicle GPS trajectories. *Sensors, 18*(4), 1261. https://doi.org/10.3390/s18041261

*Full scite-verified bibliography for the detection/evidence layers: `research/README.md`.*
