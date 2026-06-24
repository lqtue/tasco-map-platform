<script lang="ts">
  import { base } from '$app/paths';
  import { tick, onMount } from 'svelte';
  import { page } from '$app/state';
  import { LaneVisualizer, wayQuery, relRefQuery } from '$lib/osm/visualizer';
  import { PRESETS, DEFAULT_PRESET, COLUMNS } from '$lib/osm/columns';
  import { fetchOfficialLengthKm } from '$lib/osm/wikidata';
  import SearchPanel from '$lib/components/SearchPanel.svelte';
  import DiagramView from '$lib/components/DiagramView.svelte';
  import MapView from '$lib/components/MapView.svelte';
  import StatsDashboard from '$lib/components/StatsDashboard.svelte';
  import ColumnsModal from '$lib/components/ColumnsModal.svelte';
  import ExportPanel from '$lib/components/ExportPanel.svelte';
  import HelpDialog from '$lib/components/HelpDialog.svelte';
  import '$lib/components/modules.css';
  import type {
    RenderResult,
    WayStat,
    RelationMeta,
    SearchRequest,
    Intersection,
    ExportRow,
    SheetRow
  } from '$lib/osm/types';

  // ---- form / page state ------------------------------------------------
  let country = $state('vn');
  let showLanes = $state(false); // diagram display mode (config toggle); off = single-lane editing view
  let columns = $state<string[]>([...PRESETS[DEFAULT_PRESET]]); // sheet columns (preset/custom)
  // one collapsible panel open at a time, toggled from the search module's button strip
  let active = $state<'config' | 'completeness' | 'legend' | 'columns' | 'profile' | null>(null);
  // staged maxspeed edits (way id -> value); lifted here so the speed-profile panel reflects them
  let edits = $state(new Map<number, string>());

  // ---- render state -----------------------------------------------------
  let html = $state('');
  let totalStartPoints = $state(0);
  let loading = $state(false);
  let errorMsg = $state('');
  let wayCoords: RenderResult['wayCoords'] = {};

  // ---- dashboard state --------------------------------------------------
  let stats = $state<WayStat[]>([]);
  let rawLengthKm = $state(0);
  let officialKm = $state<number | null>(null);
  let meta = $state<RelationMeta | null>(null);
  let intersections = $state<Intersection[]>([]);
  let intersectionsRan = $state(false);
  let exportRows = $state<ExportRow[]>([]);
  let sheetRows = $state<SheetRow[]>([]);

  // child component instances (imperative APIs)
  let mapView: MapView;
  let diagramView: DiagramView;

  async function runSearch(req: SearchRequest) {
    loading = true;
    errorMsg = '';
    html = '';
    stats = [];
    rawLengthKm = 0;
    officialKm = null;
    meta = null;
    intersections = [];
    intersectionsRan = req.opts.intersections;
    exportRows = [];
    sheetRows = [];
    edits = new Map(); // staged edits don't carry across roads (way ids differ)
    selectedId = null;
    hoverRow = null;
    try {
      const v = new LaneVisualizer(req.opts);
      const r = await v.readData(req.query, 0);
      if (r !== 0) {
        errorMsg =
          r === -1 ? 'No elements returned by Overpass for this query.' : 'Need at least two ways.';
        return;
      }
      v.organizeWays();
      if (req.opts.adjacent) {
        try {
          await v.readData(v.buildAdjacentQuery(), 1);
        } catch {
          // adjacency is optional decoration; ignore failures
        }
      }
      if (req.opts.intersections) {
        try {
          await v.readData(v.buildCrossingQuery(), 2);
          v.computeIntersections();
        } catch {
          // intersection detection is optional; ignore failures
        }
      }
      const result = v.render(req.start);
      html = result.html;
      totalStartPoints = result.totalStartPoints;
      wayCoords = result.wayCoords;
      stats = result.stats;
      rawLengthKm = result.rawLengthKm;
      intersections = result.intersections;
      exportRows = result.exportRows;
      sheetRows = result.sheetRows;
      mapView?.showRoad(wayCoords); // draw the whole road and fit it in view
      meta = v.getRelationMeta();
      if (!html.trim()) errorMsg = 'Query returned data but no highway ways could be drawn.';
      // official length from Wikidata (non-blocking; ignore failures)
      if (meta?.wikidata) {
        fetchOfficialLengthKm(meta.wikidata)
          .then((km) => (officialKm = km))
          .catch(() => {});
      }
    } catch (e) {
      errorMsg = (e as Error).message || String(e);
    } finally {
      loading = false;
    }
  }

  // selection shared across the three surfaces (map · sheet · speed profile):
  // clicking any one focuses the same segment in all three.
  let selectedId = $state<number | null>(null);
  function select(id: number, fromMap = false) {
    selectedId = id; // marks the speed-profile bar
    diagramView?.focusWay(id); // scroll + flash the sheet row
    if (!fromMap) mapView?.zoom(wayCoords[id]); // focus the map (it self-highlights on its own clicks)
  }

  // diagram/profile → map · sheet · profile wiring
  const onHover = (id: number) => mapView?.highlightSeg(wayCoords[id]); // hover = transient map highlight
  const onZoom = (id: number) => select(id); // sheet "⊙ map" chip / profile-bar click / diagram zoom
  const onDrill = (wayid: string) =>
    runSearch({ query: wayQuery(wayid), start: 1, opts: lastOpts() });
  // map → sheet + profile: clicking a segment on the map syncs the other two
  const onPick = (id: number) => select(id, true);

  // ---- content for the toggled panels (rendered below the search strip) ----
  // full column universe for the Columns picker: computed columns + every raw tag in the data
  const allKeys = $derived.by(() => {
    const tags = new Set<string>();
    for (const r of sheetRows) for (const k of Object.keys(r.tags)) tags.add(k);
    const fixed = COLUMNS.map((c) => c.key as string);
    return [...fixed, ...[...tags].sort().filter((k) => !fixed.includes(k))];
  });
  // hatch swatch for the legend's "no lane data" entry (matches div.lane.nolane)
  const HATCH =
    'repeating-linear-gradient(-45deg,#666,#666 4px,#fff 4px,#fff 9px,#666 9px,#666 13px)';
  // speed profile (elevation-style step chart of maxspeed along the route; reflects staged edits).
  // bar height = maxspeed, bar colour = OSM edit freshness (same ramp as the /map overview).
  const CHART_H = 130;
  const STALE = 730; // days; ≥2 yr counts as fully stale (matches src/routes/map)
  const freshHue = (d: number) => `hsl(${Math.round(120 * (1 - Math.min(d, STALE) / STALE))} 70% 45%)`;
  const speedOf = (r: SheetRow) => (edits.has(r.id) ? edits.get(r.id)! : r.max);
  // selected bar wins (map-highlight red); else colour by edit age; else leave to CSS
  const barFill = (b: { id: number; age: number | null }) =>
    b.id === selectedId ? '#e6194b' : b.age == null ? '' : freshHue(b.age);
  const FRESH_STOPS = [freshHue(0), freshHue(365), freshHue(STALE)]; // legend gradient
  let profZoom = $state(1); // horizontal zoom of the profile (1 = fit width)
  let hoverRow = $state<SheetRow | null>(null); // segment under the cursor → stats tooltip
  let tipX = $state(0);
  let tipY = $state(0);
  let tipH = $state(0); // tooltip height, so it sits above the cursor (never below the chart)
  let profW = $state(0); // profile width, to keep the tooltip on-screen
  const rowById = $derived(new Map(sheetRows.map((r) => [r.id, r])));
  const profile = $derived.by(() => {
    let x0 = 0;
    const bars = sheetRows.map((r) => {
      const raw = speedOf(r);
      const v = raw === 'none' ? CHART_H : parseInt(raw, 10);
      const bar = { id: r.id, x0, w: Math.max(r.km - x0, 0.0001), v: Number.isNaN(v) ? null : v, raw, age: r.ageDays };
      x0 = r.km;
      return bar;
    });
    return { bars, totalKm: x0 || 1 };
  });

  // keep the opts of the most recent search so drill-in reuses them
  let lastReq: SearchRequest | null = null;
  function lastOpts() {
    return (
      lastReq?.opts ?? {
        country,
        usePlacement: false,
        adjacent: false,
        lanewidth: false,
        usenodes: false,
        extendway: false,
        intersections: false
      }
    );
  }
  function handleSearch(req: SearchRequest) {
    lastReq = req;
    runSearch(req);
  }

  // deep-link from the dashboard: /editor?ref=QL.1 auto-runs a relation-by-ref search
  onMount(() => {
    const ref = page.url.searchParams.get('ref');
    if (ref) handleSearch({ query: relRefQuery(ref), start: 1, opts: lastOpts() });
  });

  // ---- draggable split between diagram and map --------------------------
  let splitEl: HTMLDivElement;
  let leftFrac = $state(0.5); // share of width given to the diagram
  let dragging = $state(false);
  let showMap = $state(true); // map column hide/show (sheet goes full width when hidden)
  let headH = $state(0); // measured sticky-header height → offsets the sticky map below it

  async function toggleMap() {
    showMap = !showMap;
    if (showMap) {
      await tick(); // let the column reappear, then let Leaflet recompute its size
      mapView?.resize();
    }
  }

  function dragStart(e: PointerEvent) {
    dragging = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }
  function dragMove(e: PointerEvent) {
    if (!dragging || !splitEl) return;
    const r = splitEl.getBoundingClientRect();
    let f = (e.clientX - r.left) / r.width;
    leftFrac = Math.min(0.85, Math.max(0.15, f));
    mapView?.resize(); // keep Leaflet tiles filling the changing column
  }
  function dragEnd(e: PointerEvent) {
    dragging = false;
    (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
    mapView?.resize();
  }
</script>

<svelte:head>
  <link rel="stylesheet" href={`${base}/css/style.css`} />
  <link rel="stylesheet" href={`${base}/css/${country}.css`} />
</svelte:head>

<!-- sticky header: search strip + its button strip stay pinned while the sheet scrolls -->
<div class="head-sticky" bind:clientHeight={headH}>
  <!-- module 1: search & configuration; Hide map + Help ride in its button strip to save a row -->
  <SearchPanel bind:country bind:showLanes bind:columns bind:active hasResult={stats.length > 0} {totalStartPoints} {loading} onsearch={handleSearch}>
    {#snippet controls()}
      <button class="btn" onclick={toggleMap}>{showMap ? 'Hide map' : 'Show map'}</button>
      <HelpDialog />
    {/snippet}
  </SearchPanel>

  {#if loading}<p class="status">Loading from Overpass…</p>{/if}
  {#if errorMsg}<p class="status error">{errorMsg}</p>{/if}

  <!-- the toggled result panels (one at a time) stay pinned with the search header -->
  {#if stats.length}
  {#if active === 'completeness'}
    <StatsDashboard {stats} {rawLengthKm} {officialKm} {meta} {intersections} {intersectionsRan}>
      {#snippet actions()}
        <ExportPanel rows={exportRows} name={meta?.ref || meta?.name || 'osm-export'} />
      {/snippet}
    </StatsDashboard>
  {:else if active === 'legend'}
    <div class="module panel">
      <div class="legend">
        <div class="lg-group">
          <span class="lg-h">Lanes</span>
          <span class="lg"><i class="sw" style="background:#cdc"></i>Forward</span>
          <span class="lg"><i class="sw" style="background:#dcc"></i>Backward</span>
          <span class="lg"><i class="sw" style="background:#ccccc5"></i>Both ways</span>
          <span class="lg"><i class="sw" style={`background:${HATCH}`}></i>No lane data</span>
          <span class="lg"><i class="sw" style="background:#ccc"></i>Shoulder</span>
          <span class="lg"><i class="sw" style="background:#bde"></i>Sidewalk</span>
        </div>
        <div class="lg-group">
          <span class="lg-h">Signs</span>
          <span class="lg"><i class="circle">50</i>Speed limit</span>
          <span class="lg"><i class="badge">2</i>Intersections on segment</span>
          <span class="lg"><i class="arrow">↰↑↱</i>Turn lanes</span>
        </div>
        <div class="lg-group">
          <span class="lg-h">Route shield</span>
          {#if country === 'vn'}
            <span class="lg"><i class="shield" style="background:#168039;color:#fff">CT</i>Expressway</span>
            <span class="lg"><i class="shield" style="background:#1a5fb4;color:#fff">QL</i>National</span>
            <span class="lg"><i class="shield" style="background:#fff;color:#000;border:1px solid #000">TL</i>Provincial</span>
          {:else}
            <span class="lg"><i class="shield" style="background:#1a5fb4;color:#fff">A1</i>Coloured by road class</span>
          {/if}
        </div>
      </div>
    </div>
  {:else if active === 'columns'}
    <div class="module panel">
      <ColumnsModal {allKeys} bind:columns />
    </div>
  {:else if active === 'profile' && sheetRows.length}
    <div class="module panel">
      <!-- toolbar: zoom + colour legend -->
      <div class="prof-bar">
        <label class="prof-zoom">zoom
          <input type="range" min="1" max="24" step="0.5" bind:value={profZoom} />
        </label>
        <span class="prof-legend" title="bar height = maxspeed; colour = days since the segment's last OSM edit">
          <small>edit freshness</small>
          <span class="pl-grad" style={`background:linear-gradient(90deg,${FRESH_STOPS.join(',')})`}></span>
          <small>fresh</small><small>·</small><small>1 yr</small><small>·</small><small>≥2 yr</small>
          <i class="pl-missing"></i><small>no maxspeed</small>
        </span>
      </div>
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- svelte-ignore a11y_mouse_events_have_key_events -->
      <div
        class="profile"
        bind:clientWidth={profW}
        onmousemove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          tipX = e.clientX - r.left;
          tipY = e.clientY - r.top;
        }}
        onmouseleave={() => (hoverRow = null)}
      >
        <div class="y-labels"><span>120</span><span>90</span><span>50</span><span>0</span></div>
        <div class="prof-scroll">
          <svg viewBox="0 0 {profile.totalKm} {CHART_H}" preserveAspectRatio="none" style={`width:${profZoom * 100}%`} role="img" aria-label="speed profile">
            {#each [50, 90, 120] as g (g)}
              <line x1="0" x2={profile.totalKm} y1={CHART_H - g} y2={CHART_H - g} class="grid" />
            {/each}
            {#each profile.bars as b (b.id)}
              {@const fill = barFill(b)}
              {#if b.v === null}
                <rect x={b.x0} width={b.w} y={CHART_H - 8} height="8" class="nodata" style={fill ? `fill:${fill}` : undefined} role="presentation"
                  onmouseenter={() => { onHover(b.id); hoverRow = rowById.get(b.id) ?? null; }} onclick={() => onZoom(b.id)} />
              {:else}
                <rect x={b.x0} width={b.w} y={CHART_H - b.v} height={b.v} class="bar" style={fill ? `fill:${fill}` : undefined} role="presentation"
                  onmouseenter={() => { onHover(b.id); hoverRow = rowById.get(b.id) ?? null; }} onclick={() => onZoom(b.id)} />
              {/if}
            {/each}
          </svg>
        </div>
        {#if hoverRow}
          {@const r = hoverRow}
          <div class="prof-tip" bind:clientHeight={tipH} style={`left:${Math.max(2, Math.min(tipX + 12, profW - 234))}px;top:${Math.max(2, tipY - tipH - 10)}px`}>
            <div class="pt-h">way {r.id}{#if r.nameHtml} · {@html r.nameHtml}{/if}</div>
            <div class="pt-row"><b>{speedOf(r) || '—'}</b> km/h maxspeed</div>
            <div class="pt-row">{r.lengthM} m · at km {r.km.toFixed(1)}</div>
            <div class="pt-row">{r.highway || '—'}{#if r.lanes} · {r.lanes} lanes{/if}{#if r.dual} · divided{/if}</div>
            <div class="pt-row">{r.ageDays == null ? 'no edit date' : `edited ${r.ageDays} d ago`}</div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
  {/if}
</div>

<!-- module 3: split screen — diagram | (drag) | map -->
<div
  class="split"
  class:dragging
  class:no-map={!showMap}
  bind:this={splitEl}
  style={(showMap ? `grid-template-columns:${leftFrac}fr 8px ${1 - leftFrac}fr` : 'grid-template-columns:1fr') + `;--head-h:${headH}px`}
>
  <DiagramView bind:this={diagramView} {html} {sheetRows} bind:columns bind:edits {showLanes} onhover={onHover} onzoom={onZoom} ondrill={onDrill} />
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="gutter"
    role="separator"
    aria-orientation="vertical"
    onpointerdown={dragStart}
    onpointermove={dragMove}
    onpointerup={dragEnd}
    title="Drag to resize"
  ></div>
  <!-- map cell: the Leaflet map (the route being edited) -->
  <div class="map-cell">
    <MapView bind:this={mapView} onpick={onPick} />
  </div>
</div>

<style>
  /* search strip + its buttons pinned to the top while the sheet scrolls under them */
  .head-sticky {
    position: sticky;
    top: 0;
    z-index: 10;
    background: #fff;
    padding: 6px 0 8px;
    border-bottom: 1px solid #e2e7ee;
  }
  .status {
    clear: both;
    font-weight: bold;
  }
  .status.error {
    color: #b00;
  }

  /* split: diagram | draggable gutter | full-height sticky map */
  .split {
    display: grid;
    align-items: start;
    clear: both;
  }
  .split.dragging {
    cursor: col-resize;
    user-select: none;
  }
  /* stretch the map cell to the full grid-row height so the sticky map inside it
     (.mapwrap) has room to travel while the taller diagram column scrolls */
  .map-cell {
    align-self: stretch;
  }
  /* map hidden: drop the gutter + map cell, diagram takes the single 1fr column */
  .split.no-map .gutter,
  .split.no-map .map-cell {
    display: none;
  }
  .gutter {
    align-self: stretch;
    min-height: 200px;
    cursor: col-resize;
    background: #e3e3e3;
    border-radius: 4px;
    position: sticky;
    top: calc(var(--head-h, 90px) + 8px);
    height: calc(100vh - var(--head-h, 90px) - 16px);
  }
  .gutter:hover,
  .split.dragging .gutter {
    background: #9bb4d6;
  }

  @media (max-width: 900px) {
    .split {
      grid-template-columns: 1fr !important;
    }
    .gutter {
      display: none;
    }
  }

  /* ---- toggled panels (legend / speed profile): the .module wrapper is the container ---- */
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 22px;
    font-family: sans-serif;
    font-size: 12px;
  }
  .lg-group {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 12px;
  }
  .lg-h {
    font-weight: 700;
    color: #374151;
  }
  .lg {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: #4b5563;
  }
  .sw {
    width: 18px;
    height: 12px;
    border: 1px dashed #fff;
    outline: 1px solid #cbd2dc;
    flex: none;
  }
  .circle {
    width: 18px;
    height: 18px;
    border: 3px solid red;
    border-radius: 50%;
    background: #fff;
    color: #000;
    font-size: 9px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
  }
  .badge {
    min-width: 16px;
    height: 16px;
    padding: 0 3px;
    border: 1px solid #000;
    border-radius: 9px;
    background: #f0e060;
    font-size: 10px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
  }
  .arrow {
    font-size: 13px;
    color: #333;
    letter-spacing: -1px;
  }
  .shield {
    min-width: 22px;
    height: 16px;
    padding: 0 3px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
  }

  /* profile toolbar: zoom slider + colour legend */
  .prof-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px 18px;
    margin-bottom: 6px;
    font-size: 11px;
    color: #6b7280;
  }
  .prof-zoom {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .prof-zoom input {
    width: 120px;
  }
  .prof-legend {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .pl-grad {
    width: 96px;
    height: 10px;
    border-radius: 2px;
    border: 1px solid #cbd2dc;
  }
  .pl-missing {
    width: 12px;
    height: 10px;
    border-radius: 2px;
    background: #e5a3a3;
    display: inline-block;
    margin-left: 8px;
  }

  .profile {
    position: relative;
    padding-left: 26px;
  }
  .prof-scroll {
    overflow-x: auto;
    overscroll-behavior-x: contain;
  }
  /* hover stats tooltip */
  .prof-tip {
    position: absolute;
    z-index: 6;
    pointer-events: none;
    max-width: 230px;
    background: #111827;
    color: #f9fafb;
    font-size: 11px;
    line-height: 1.4;
    padding: 6px 8px;
    border-radius: 5px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.28);
  }
  .prof-tip .pt-h {
    font-weight: 700;
    margin-bottom: 3px;
  }
  .prof-tip .pt-row {
    color: #d1d5db;
  }
  .prof-tip b {
    color: #fde68a;
    font-weight: 700;
  }
  .profile svg {
    display: block;
    width: 100%;
    height: 90px;
  }
  .profile :global(.bar) {
    fill: #60a5fa;
  }
  .profile :global(.bar):hover {
    fill: #2563eb;
  }
  .profile :global(.nodata) {
    fill: #e5a3a3;
  }
  .profile :global(.grid) {
    stroke: #e5e7eb;
    stroke-width: 1;
    vector-effect: non-scaling-stroke;
  }
  .y-labels {
    position: absolute;
    left: 0;
    top: 0;
    height: 90px;
    width: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    font-size: 9px;
    color: #9aa3af;
    padding: 2px;
    box-sizing: border-box;
  }
</style>
