# CLAUDE.md — lanes/ (OSM Lane & Road-Attribute Visualizer)

Guidance for working in this module. See the repo-root `CLAUDE.md` for the wider project.

## What this is

A SvelteKit (static, client-only) road-attribute visualizer for OSM, focused on Vietnam, used
as the QA front-end **and maxspeed editor** for the road-by-road enrichment work (and the
deferred lanes problem). Serves **O3KR1.1 (maxspeed)**. **Branded "TASCO MapOps Toolkit"** in the
UI (nav `src/routes/+layout.svelte`, page title `src/app.html`) — one of the two active web apps
(the other is `traffic/sat-imagery/`), published to GitHub Pages at
<https://lqtue.github.io/tasco-map-platform/mapops-toolkit/>.

> **Where this is heading:** the **metadata-editing track** of the **MapOps Toolkit** (the agreed
> name for the whole O3 editing system) — local PBF ↔ versioned **Editor DB (PostGIS)** ↔ OSC/XML ↔
> production + live OSM, with a geometry & QA track (Quân / RouteSense + JOSM/GeoLibre) alongside, and
> Bayesian + decision-tree suggestions fed from multi-source observations. System intro + how-to +
> PostGIS schema: [`docs/editor-platform.html`](docs/editor-platform.html). The table editor here is
> the seed of the metadata track (presets: maxspeed → maxheight / turn / lanes).

**Two routes** (shared nav in `src/routes/+layout.svelte`):
- **`/` — the national-road status dashboard** (`src/routes/+page.svelte`): the landing page. A
  sortable/filterable table of all route relations (centerline km, maxspeed coverage bar, missing
  km = worklist, **a per-route speed-profile sparkline coloured by OSM edit freshness**, median
  edit-age, connectivity gaps) over headline coverage cards. Static-data only (no Overpass): reads
  `static/data/route_coverage.json` (from `traffic/maxspeed/baseline/route_coverage.py`) +
  `static/data/route_freshness.json` (from `route_freshness.py` — per-route `[maxspeed,age_days]`
  bins + length-weighted median edit-age; regenerate from the PBF and copy into `static/data/`).
  Each row's **Open →** deep-links `/editor?ref=QL.1`.
- **`/map` — the national overview map** (`src/routes/map/+page.svelte`): a Leaflet (canvas-renderer)
  map of the QL + CT network, every segment recolourable by **maxspeed coverage / speed value / edit
  freshness** (radio toggle, `layer.setStyle` in place). Static-data only: reads
  `static/data/national_roads.geojson` (from `traffic/maxspeed/baseline/route_map.py` — simplified
  LineStrings with `{ref, ms, age}`; ~6 MB, regenerate from the PBF and copy in). Segment popup →
  Open in editor. The dashboard sparkline is also a link into `/editor?ref=`.
- **`/editor` — the lane visualizer / maxspeed editor** (`src/routes/editor/+page.svelte`): the live
  Overpass tool below. Honours `?ref=` to auto-run a relation-by-ref search on mount.

It began as a faithful rewrite of the Perl tool
[mueschel/OSMLaneVisualizer](https://github.com/mueschel/OSMLaneVisualizer) — that upstream
(`OSMData.pm` + `OSMLanes.pm` + `OSMDraw.pm` + `render.pl`) is the behavioral reference for the
**full-lane diagram**; it is **not vendored here**, clone it from GitHub if you need to consult
it.

The default left-pane view is **not** the ported diagram but a native editable **sheet** (one
row per way) for staging maxspeed edits; the ported `{@html}` diagram only renders when the
"Show full lanes" config toggle is on. The tool never writes to OSM — edits are staged locally
and copied out as `way,maxspeed` CSV to apply in iD/JOSM with street-view evidence (per the
repo-root scope pivot).

## Commands

All commands run inside `traffic/lanes/`:

```bash
npm install
npm run dev      # vite dev server
npm run build    # static site -> ./build (adapter-static, prerendered SPA)
npm run preview  # serve the production build
npm run check    # svelte-kit sync + svelte-check (type check)
```

There is **no test suite**. After any change to `visualizer.ts` or the components, verify with
**`npm run build` AND `npm run check`**.

**Known-acceptable `svelte-check` errors (pre-existing, do NOT try to "fix"):**
- 4× `makeShoulder`/`makeSidewalk` "comparison appears unintentional ... 'no'" in
  `visualizer.ts` (faithful port of Perl logic).
- 1× `leaflet` "Could not find a declaration file" in `MapView.svelte` (no `@types/leaflet`).

A clean run = exactly these 5 errors and nothing new.

## Architecture

Client-only SPA. No backend — all data is fetched from public APIs directly in the browser.
`src/routes/+layout.ts` sets `ssr = false; prerender = true`.

### Data flow (one search)

```
SearchPanel (build Overpass query)
  -> +page.svelte runSearch()
       new LaneVisualizer(opts)
       v.readData(query, 0)            // main road ways  -> store slot 0
       v.organizeWays()                // chain ways by shared begin/end nodes
       [opts.adjacent]  v.readData(buildAdjacentQuery(), 1)
       [opts.intersections] v.readData(buildCrossingQuery(), 2); v.computeIntersections()
       result = v.render(start)        // -> { html, sheetRows, wayCoords, stats, intersections, rawLengthKm, exportRows }
       v.getRelationMeta() -> wikidata -> fetchOfficialLengthKm()
  -> DiagramView (left pane): editable sheet from result.sheetRows  (or {@html result.html} when showLanes)
  -> MapView (right pane, Leaflet)
  -> panels (one at a time): StatsDashboard | Legend | Columns | Speed profile
```

**State ownership / the panel accordion.** `+page.svelte` is the single source of truth. It
owns `active` (`'config'|'completeness'|'legend'|'columns'|'profile'|null` — **one panel open at
a time**, toggled from the button strip in `SearchPanel`), the staged-edit `Map<wayId,maxspeed>`
(`edits`, lifted here so the speed-profile reflects it), `columns` (sheet column set), and
`showMap` (hide/show the map column, kept mounted via CSS so Leaflet state survives). The four
result panels render in a `.module` container right under the search strip; `SearchPanel` only
flips `active`, the panel **content** lives in `+page` (legend markup, `<ColumnsModal>`, the
speed-profile SVG) or its own component (`StatsDashboard`). Each panel/`.btn` uses the shared
`.module`/`.btn`/`.btn.on` chrome in `src/lib/components/modules.css`.

### `src/lib/osm/visualizer.ts` — the core (one big ported class)

`LaneVisualizer` holds a multi-slot `store` (`store.way[0|1|2]`, `store.node[...]`,
`store.rel[...]`): slot 0 = the road itself, slot 1 = adjacent ways, slot 2 = crossing roads.

- **HTML emission**: `drawWay()` + `render()` emit HTML using the **exact same class names** as
  the original `style.css`/`<country>.css`. Deliberate — the CSS in `static/css/` is reused
  verbatim, so changing emitted class names breaks styling. New visual elements get new classes
  added to `static/css/style.css`.
- **Lane parsing** (`getLanes`, `inspectLanes`, `getLaneTags`): faithful port. One quirk
  preserved intentionally — pushing `undefined` makes `definedMax` true, so the `lanes/2`
  symmetric-split default is dead code, matching Perl. Result: a non-oneway `lanes=4` way with
  no directional split renders 1 fwd + 1 bck + 2 hatched `nolane`.
- **Geometry**: `calcDistance`/`calcLength` (meters, equirectangular approx), `calcDirection`
  (custom Perl-convention bearing), plus a standard `compass()` (atan2, 0=N clockwise) used only
  for intersection turn direction.
- **Stats** (added beyond the original): `collectStat()` per way feeds `stats: WayStat[]`
  (length + length-weighted coverage flags); `render()` returns `rawLengthKm`.
- **Sheet rows** (added): `drawWay()` also pushes a `SheetRow` per way (see `types.ts`) carrying
  structured fields the editable sheet needs — id, km, length, ref/name HTML, current `max` +
  morphology (`highway`/`lanes`/`oneway`/`dual`), the derived `category`
  (`motorway`/`dual`/`single`), the **Thông tư 38 legal defaults** `legalUrban`/`legalRural`, and
  the **raw `tags`** (so any tag, incl. per-vehicle `maxspeed:*`, can become a sheet column).
- **Carriageway pairing** (added): `pairCarriageways()` runs at the end of `render()` and fills
  `wayCoords[id].pairId` for divided highways (OSM models them as two opposing one-way ways
  sharing no nodes) by matching opposite bearing (±35°) within ≤60 m lateral. The map draws the
  mate as a green dashed line when a segment is focused.
- **Intersections** (added): `buildCrossingQuery()` (`way(bn.<our nodes>)[highway]` minus our
  own, with `>;out skel` for coords) + `computeIntersections()` → a node shared with another
  highway is a junction. Filters non-vehicular classes and ways whose `ref` matches our road
  (continuations). Per-segment counts render as a `.xcount` badge; per-node markers + Mapillary
  links go on the map.
- **Country shields**: `refClass()` maps refs to shield classes per country. Vietnam (`vn`):
  `CT→A` (expressway, green), `QL→B` (national, blue), `AH|E→E`, `DT|ĐT|TL→K` (provincial).
- **Overpass resilience**: `fetchOverpass()` walks `OVERPASS_ENDPOINTS` (de → kumi → mail.ru
  mirror); treats any body not starting with `{` as an error page (avoids the
  `JSON Parse error: '<'` crash) and throws a friendly message only if all mirrors fail.

### Components (`src/lib/components/`)

Thin modules orchestrated by `+page.svelte` (which owns the state — see above):
- **SearchPanel** — builds the Overpass query via exported
  `wayQuery`/`relQuery`/`relNameQuery`/`relRefQuery`, emits `onsearch(SearchRequest)`; owns the
  diagram-drawing config (`cfg`, `showLanes`, `start`, `country`) in its Configuration panel.
  Also renders the **button strip** that drives the page's `active` panel (`bind:active`). `country`
  is `$bindable` shared with the page (drives the `<country>.css` link).
- **DiagramView** — the **editable maxspeed sheet** (default) built from `sheetRows` + the
  `columns` set: inline `<select>` per row writing to the bound `edits` map, one-click U/R legal
  defaults, checkbox + Shift-range selection → bulk speed, per-row tool chips (Mapillary/iD/JOSM/
  level0 + zoom/solo). Falls back to `{@html html}` (full-lane mode) when `showLanes`, where it
  delegates DOM events: hover `.label` → `onhover`, click `.label` → `onzoom`, click
  `[data-wayid]` → `ondrill`. Exposes `focusWay(id)` (map → sheet scroll/flash).
- **ColumnsModal** — despite the name it's an **inline panel** (not a dialog): the full
  column-picker (presets + every computed column + every raw tag found in the data), `bind:columns`.
- **MapView** — encapsulates Leaflet; imperative `showRoad()`/`highlightSeg()`/`zoom()`/`resize()`
  via `bind:this`; `onpick` (map click → page → `DiagramView.focusWay`). Draws the focused
  segment's paired carriageway (`pairId`) as a green dashed line; `WayGeom.crossings` become
  amber Mapillary markers. A **Mapillary speed-sign overlay** (Map options → toggle + token) draws
  already-detected speed-limit signs in the current viewport as red-ringed km/h markers (evidence
  to match against staged edits), refetched on pan/zoom; the fetch helper is `$lib/osm/mapillary.ts`
  (browser twin of `traffic/signs/mapillary_signs.py`), token kept in `localStorage`.
- **StatsDashboard** — `$derived` coverage %, length headline (raw vs decoupled estimate vs
  Wikidata official), intersection counts; export lives in its header snippet.
- **ExportPanel / HelpDialog** — CSV/JSON export with per-column selection; how-to-use dialog.

`+page.svelte` also implements the draggable split between DiagramView and MapView.

### The maxspeed editing sheet

`src/lib/osm/columns.ts` is the single source for the sheet's columns: `COLUMNS` (canonical
order + width — rows are always rendered in this order, filtered to the enabled keys, so a preset
is just a membership set), `PRESETS` (default **`Max speed`** = the Thông tư 38 decision-tree
inputs: morphology + current speed + the computed legal default), `SPEEDS` (inline-editor
values), and `colDef(key)` (falls back to a generic def for raw-tag keys). Edits are **staged**
in the page's `edits` map (blue ring on changed cells), never written to OSM; Copy emits
`way,maxspeed` CSV. The **speed-profile** panel is an elevation-style step chart of maxspeed vs
distance that recomputes from `edits`, so it updates live as you edit.

### Conventions specific to this codebase

- Svelte 5 runes (`$state`, `$derived`, `$props`, `$bindable`). Callback props, not
  `createEventDispatcher`.
- The diagram emits raw HTML strings (a port of the Perl), injected with `{@html}`. Escape
  user/tag-derived text with `escapeEntities()`; HTML uses entities (`&#x2191;`), not unicode.
- `import { sveltekit } from '@sveltejs/kit/vite'` in `vite.config.ts` (NOT from
  `vite-plugin-svelte` — that import name doesn't exist there).
- Two CSS worlds: the **ported** `static/css/style.css` + `<country>.css` (verbatim, class names
  are a contract with `visualizer.ts`) for the `{@html}` diagram; the **native** sheet/panels use
  scoped component styles + the shared chrome in `src/lib/components/modules.css` (`.module`,
  `.btn`, `.btn.on`). New sheet/panel UI goes in `modules.css`/component styles, not `style.css`.
- Adding a country = add `static/css/<code>.css` (reuse `style.css` classes) + a branch in
  `refClass()` + an `<option>` in SearchPanel + a `Route shield` legend branch in `+page.svelte`.
- Adding a sheet column = add to `COLUMNS`/a preset in `columns.ts` and a `{#if c.key === …}`
  branch in `DiagramView`; any raw OSM tag is already selectable without code (generic cell).
- `svelte.config.js` reads `BASE_PATH` for sub-path hosting (GitHub Pages); local dev stays at
  root. **Published manually** (no Actions workflow): `BASE_PATH=/tasco-map-platform/mapops-toolkit
  npm run build`, then copy `build/` into the `gh-pages` branch under `mapops-toolkit/` (a
  `.nojekyll` at the gh-pages root is required so the `_app/` dir is served). The `gh-pages` branch
  also hosts `sat-imagery/` + a landing `index.html`.
