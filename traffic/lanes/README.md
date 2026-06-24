# lanes/ — OSM Lane & Road-Attribute Visualizer

A browser-based visualizer for OpenStreetMap lane/road attributes, focused on Vietnam roads
as part of the enrichment QA workflow. It renders a road's lanes, speed limits, turn lanes,
destination signs, intersections and more as a schematic diagram synced to a live map —
entirely client-side, no backend.

A SvelteKit rewrite of the Perl tool
[mueschel/OSMLaneVisualizer](https://github.com/mueschel/OSMLaneVisualizer), extended with a
completeness dashboard, intersection detection, official-length comparison (Wikidata) and a
resizable split diagram/map view.

> **Not just lanes.** Despite the folder name, this is the **road-attribute QA tool** for the
> live maxspeed road-by-road work (scope pivot 2026-06-15): the completeness dashboard scores
> `maxspeed` coverage per road, the length comparison diffs OSM km vs official Wikidata km, and
> the per-segment Mapillary links give the street-view evidence every edit needs. It also
> covers the deferred lanes problem (#3 in `../../PROJECT_PLAN.md`).

## Features

- **Lane diagram** — per-segment lanes with direction, `turn:lanes`, `maxspeed[:lanes]`,
  destination/exit signs, access, shoulders, sidewalks, placement and change lines. Emits the
  original tool's CSS class names, so the upstream stylesheets are reused as-is.
- **Completeness dashboard** — length-weighted coverage % for maxspeed, lanes, turn, surface,
  lit, width, shoulder, sidewalk, bridge/tunnel and access; plus a maxspeed value distribution.
- **Length comparison** — OSM raw length vs a decoupled (dual-carriageway) estimate vs the
  **official length from Wikidata** (property P2043, via the relation's `wikidata` tag).
- **Intersection detection** — finds roads crossing the loaded one (a shared node with another
  highway), shown as a per-segment count by road type, with amber map markers that link to
  Mapillary for sign checking.
- **Split view** — diagram left, full-height Leaflet map right, draggable divider; hover a way
  to preview, click a row to zoom.
- **Data export** — every drawn way's computed fields + raw OSM tags, as CSV or JSON with
  per-column selection.
- **Vietnam route shields** — `CT` expressway (green), `QL` national (blue), `DT/ĐT/TL`
  provincial, `AH` Asian Highway. German (`de`) and Belgian (`be`) packs included.

## Quick start

All commands run from this directory (`traffic/lanes/`):

```bash
npm install
npm run dev      # vite dev server, open the printed localhost URL
npm run build    # static site -> ./build (adapter-static, prerendered SPA)
npm run check    # type-check (svelte-check) — see CLAUDE.md for the 5 known-acceptable errors
```

Pick country **vn**, enter a relation ref such as `QL.51` (or a way/relation id), and click
**Search**. Data is fetched live from the Overpass API (with mirror fallback) in the browser.

## Using it

**Search panel.** Pick a **Country** (drives route-shield colours), a **Search by** mode, type
the ref/name/id, **Search**. **Configuration** (collapsible) holds the options — hover each for
a one-line explanation; "Start at end number" picks which chain end to begin drawing from.

**Completeness panel.** Two headline scores (attributes tagged, length vs official) plus
per-attribute coverage bars, worst first. **Details** expands a maxspeed distribution.
**⬇ Export data** downloads every drawn way as CSV or JSON. **Legend** explains the colours.

**Diagram ↔ map.** Each way row links: **(M)** Mapillary, **(J)** JOSM remote-control,
**(L)** level0, **(R)** Rapid/iD, **(Z)** zoom to segment, **(V)** reload just that way.
Crossing roads show as amber markers linking to Mapillary. Drag the divider to resize.

## How it works

A single ported class (`src/lib/osm/visualizer.ts`) loads OSM data from Overpass into a
multi-slot store (road / adjacent ways / crossing roads), chains ways by shared end nodes, and
emits an HTML lane diagram. `src/routes/+page.svelte` orchestrates the `SearchPanel`,
`StatsDashboard`, `DiagramView` and `MapView` modules and wires the diagram to the map.
Official lengths come from `src/lib/osm/wikidata.ts`. See [`CLAUDE.md`](CLAUDE.md) for full
architecture notes.

| File | Origin |
|------|--------|
| `src/lib/osm/visualizer.ts` | port of `OSMData.pm` + `OSMLanes.pm` + `OSMDraw.pm` + `render.pl` |
| `src/lib/osm/wikidata.ts` | official road length (Wikidata property P2043) |
| `src/lib/osm/types.ts` | data model |
| `src/routes/+page.svelte` | orchestrates modules; diagram↔map wiring; draggable split |
| `src/lib/components/*.svelte` | SearchPanel · StatsDashboard · DiagramView · MapView · ExportPanel · HelpDialog |
| `static/css/{style,de,be,vn}.css` | reused verbatim from the original — the port emits the same class names |

> VN traffic-sign / destination-symbol images currently reuse the German placeholders — swap
> the URLs in `static/css/vn.css` for Vietnamese signage.

## Tech

SvelteKit 2 · Svelte 5 (runes) · TypeScript · Leaflet · adapter-static (client-only SPA) ·
Overpass API · Wikidata · Mapillary links.

## Credits

Lane-rendering logic and stylesheets derived from
[mueschel/OSMLaneVisualizer](https://github.com/mueschel/OSMLaneVisualizer) (kept upstream as
read-only reference, not vendored here). Map data © OpenStreetMap contributors.
