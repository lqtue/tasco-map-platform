<script lang="ts">
  import { JOSM_BASE } from '$lib/osm/visualizer';
  import { colDef, SPEEDS } from '$lib/osm/columns';
  import type { SheetRow } from '$lib/osm/types';

  let {
    html = '',
    sheetRows = [],
    columns = $bindable<string[]>([]),
    edits = $bindable(new Map<number, string>()), // staged maxspeed edits, owned by the page
    showLanes = false, // off (default) = the single-lane editing sheet; on = full lane diagram
    onhover,
    onzoom,
    ondrill
  }: {
    html: string;
    sheetRows?: SheetRow[];
    columns?: string[];
    edits?: Map<number, string>;
    showLanes?: boolean;
    onhover: (id: number) => void;
    onzoom: (id: number) => void;
    ondrill: (wayid: string) => void;
  } = $props();

  let scrollEl: HTMLDivElement; // scrolling viewport (sheet rows / full-lane diagram)
  let picked: HTMLElement | null = null;

  // active columns in chosen order; grid template (leading 30px checkbox) shared by
  // header + rows so they line up. Unknown keys (raw tags) get a generic def.
  const activeCols = $derived(columns.map(colDef));
  const gridCols = $derived(['30px', ...activeCols.map((c) => c.width)].join(' '));

  // ---- staged maxspeed edits (not written to OSM — applied in iD/JOSM w/ evidence) ----
  const speedOf = (r: SheetRow) => (edits.has(r.id) ? edits.get(r.id)! : r.max);
  const isEdited = (r: SheetRow) => edits.has(r.id) && edits.get(r.id) !== r.max;
  function setSpeed(id: number, v: string) {
    const m = new Map(edits);
    m.set(id, v);
    edits = m;
  }
  function bulkSpeed(v: string) {
    if (!v && v !== '') return;
    const m = new Map(edits);
    for (const id of selected) m.set(id, v);
    edits = m;
  }
  function clearEdits() {
    edits = new Map();
  }
  function copyEdits() {
    const body = [...edits].map(([id, v]) => `${id},${v}`).join('\n');
    navigator.clipboard?.writeText('way,maxspeed\n' + body);
  }
  let bulkVal = $state('');

  // ---- row selection: checkbox per row, Shift+click selects the span (first→last) ----
  let selected = $state(new Set<number>());
  let lastIdx: number | null = null;
  const allSelected = $derived(sheetRows.length > 0 && selected.size === sheetRows.length);
  function rowToggle(idx: number, e: MouseEvent) {
    e.preventDefault();
    const next = new Set(selected);
    if (e.shiftKey && lastIdx !== null) {
      const [a, b] = [Math.min(lastIdx, idx), Math.max(lastIdx, idx)];
      for (let i = a; i <= b; i++) next.add(sheetRows[i].id);
    } else {
      const id = sheetRows[idx].id;
      next.has(id) ? next.delete(id) : next.add(id);
    }
    selected = next;
    lastIdx = idx;
  }
  function toggleAll() {
    selected = allSelected ? new Set() : new Set(sheetRows.map((r) => r.id));
    lastIdx = null;
  }

  // called from the page when a segment is clicked on the map: scroll to it and flash.
  export function focusWay(id: number) {
    const el = scrollEl?.querySelector(`[data-way="${id}"]`) as HTMLElement | null;
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    picked?.classList.remove('picked');
    el.classList.add('picked');
    picked = el;
  }

  // editor deep-links for a segment (mirror the ones the ported diagram emits)
  const mapillary = (r: SheetRow) =>
    `http://www.mapillary.com/app/?lat=${r.lat.toFixed(5)}&lng=${r.lon.toFixed(5)}&z=16`;
  const josm = (r: SheetRow) =>
    `${JOSM_BASE}/load_and_zoom?left=${(r.lon - 0.01).toFixed(5)}&right=${(r.lon + 0.01).toFixed(5)}&top=${(r.lat + 0.005).toFixed(5)}&bottom=${(r.lat - 0.005).toFixed(5)}&select=way${r.id}`;
  const level0 = (r: SheetRow) => `http://level0.osmz.ru/?url=way/${r.id}!`;
  const rapid = (r: SheetRow) =>
    `https://rapideditor.org/edit#id=w${r.id}&map=18/${r.lat.toFixed(5)}/${r.lon.toFixed(5)}`;

  // delegation for the full-lane {@html} diagram (sheet mode wires events directly)
  function over(e: MouseEvent) {
    const label = (e.target as HTMLElement).closest('.label') as HTMLElement | null;
    if (label?.dataset.way) onhover(Number(label.dataset.way));
  }
  function click(e: MouseEvent) {
    const target = e.target as HTMLElement;
    const z = target.closest('[data-zoom]') as HTMLElement | null;
    if (z?.dataset.zoom) {
      onzoom(Number(z.dataset.zoom));
      return;
    }
    const drill = target.closest('[data-wayid]') as HTMLElement | null;
    if (drill?.dataset.wayid) ondrill(drill.dataset.wayid);
  }
</script>

<!-- single root element: this component is one cell of the page's 3-col grid -->
<div class="diagram-pane">
  <!-- staged-edit bar (contextual to the sheet; the toggle panels live in the search module) -->
  {#if html && !showLanes && edits.size}
    <div class="edits-bar">
      <span class="edits">{edits.size} speed edit{edits.size > 1 ? 's' : ''}</span>
      <button class="btn" onclick={copyEdits} title="copy way,maxspeed for applying in an editor">Copy</button>
      <button class="btn" onclick={clearEdits}>Clear edits</button>
    </div>
  {/if}

  <div class="diagram-scroll" bind:this={scrollEl}>
    {#if showLanes}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- svelte-ignore a11y_mouse_events_have_key_events -->
      <div class="diagram" onmouseover={over} onclick={click} role="presentation">
        {@html html}
      </div>
    {:else}
      {#if selected.size}
        <div class="sel-bar">
          {selected.size} selected
          <label>set speed
            <select bind:value={bulkVal} onchange={() => bulkSpeed(bulkVal)}>
              {#each SPEEDS as s (s)}<option value={s}>{s === '' ? '—' : s}</option>{/each}
            </select>
          </label>
          <button type="button" onclick={() => (selected = new Set())}>clear selection</button>
        </div>
      {/if}
      <div class="sheet" style={`--cols:${gridCols}`}>
        <div class="row head">
          <span class="c-sel"><input type="checkbox" checked={allSelected} onclick={toggleAll} title="select all" /></span>
          {#each activeCols as c (c.key)}<span>{c.label}</span>{/each}
        </div>
        {#each sheetRows as r, i (r.id)}
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <!-- svelte-ignore a11y_mouse_events_have_key_events -->
          <div class="row" class:sel={selected.has(r.id)} data-way={r.id} onmouseenter={() => onhover(r.id)}>
            <span class="c-sel">
              <input type="checkbox" checked={selected.has(r.id)} onclick={(e) => rowToggle(i, e)} title="Shift+click to select a range" />
            </span>
            {#each activeCols as c (c.key)}
              {#if c.key === 'way'}
                <span class="c-way"><a href={`https://www.openstreetmap.org/way/${r.id}`} target="_blank" rel="noopener">{r.id}</a></span>
              {:else if c.key === 'length'}
                <span class="c-len">{r.lengthM} m<small>km {r.km.toFixed(1)}</small></span>
              {:else if c.key === 'name'}
                <span class="c-name">{@html r.refHtml}<span class="nm">{@html r.nameHtml}</span></span>
              {:else if c.key === 'class'}
                <span class="c-cell">{r.highway || '—'}</span>
              {:else if c.key === 'lanes'}
                <span class="c-cell num">{r.lanes ?? '—'}</span>
              {:else if c.key === 'oneway'}
                <span class="c-cell arrow" title={r.oneway ? 'oneway carriageway' : 'two-way'}>{r.oneway ? (r.dir === 'backward' ? '←' : '→') : '↔'}</span>
              {:else if c.key === 'dual'}
                <span class="c-cell" title={r.dual ? 'dual_carriageway=yes' : ''}>{r.dual ? '✓' : ''}</span>
              {:else if c.key === 'maxspeed'}
                <span class="c-speed dir-{r.dir}" class:edited={isEdited(r)}>
                  <select class="spd" value={speedOf(r)} onchange={(e) => setSpeed(r.id, e.currentTarget.value)} title="set maxspeed">
                    {#if speedOf(r) && !SPEEDS.includes(speedOf(r))}<option value={speedOf(r)}>{speedOf(r)}</option>{/if}
                    {#each SPEEDS as s (s)}<option value={s}>{s === '' ? '—' : s}</option>{/each}
                  </select>
                </span>
              {:else if c.key === 'suggest'}
                <span class="c-cell suggest">
                  <button type="button" title="apply Urban (in built-up) legal default" onclick={() => setSpeed(r.id, r.legalUrban)}>U{r.legalUrban}</button>
                  <button type="button" title="apply Rural (outside built-up) legal default" onclick={() => setSpeed(r.id, r.legalRural)}>R{r.legalRural}</button>
                </span>
              {:else if c.key === 'tools'}
                <span class="c-tools">
                  <a class="chip" title="Mapillary street-view imagery here" target="_blank" rel="noopener" href={mapillary(r)}>📷</a>
                  <a class="chip" title="Edit this way in Rapid (iD)" target="_blank" rel="noopener" href={rapid(r)}>iD</a>
                  <a class="chip" title="Open this way in JOSM" target="_blank" rel="noopener" href={josm(r)}>JOSM</a>
                  <a class="chip" title="Open this way in the level0 editor" target="_blank" rel="noopener" href={level0(r)}>L0</a>
                  <span class="div"></span>
                  <button class="chip act" type="button" title="Zoom the map to this segment" onclick={() => onzoom(r.id)}>⊙ map</button>
                  <button class="chip act" type="button" title="Show only this way" onclick={() => ondrill(String(r.id))}>solo</button>
                </span>
              {:else}
                <span class="c-cell tag" title={`${c.key}=${r.tags[c.key] ?? ''}`}>{r.tags[c.key] ?? ''}</span>
              {/if}
            {/each}
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .diagram-pane {
    min-width: 0; /* allow the grid cell to shrink instead of forcing the column wide */
  }

  .edits-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  .edits-bar .edits {
    font-size: 12px;
    font-weight: 600;
    color: #1d4ed8;
  }

  .diagram-scroll {
    min-width: 0;
    overflow-x: auto;
    overflow-y: hidden;
    overscroll-behavior: contain;
  }

  /* ---- single-lane editing sheet: columns are preset/custom-driven ---- */
  .sheet {
    font-size: 12px;
    color: #374151;
    user-select: none; /* so Shift+click selects rows, not page text */
  }
  .sel-bar {
    position: sticky;
    top: 0;
    z-index: 4;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 8px;
    background: #fde68a;
    font-weight: 600;
  }
  .sel-bar label {
    font-weight: 400;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .sel-bar button {
    font: inherit;
    border: 0;
    background: none;
    color: #1d4ed8;
    cursor: pointer;
    text-decoration: underline;
  }
  .row {
    display: grid;
    grid-template-columns: var(--cols);
    gap: 0 8px;
    align-items: center;
    padding: 5px 8px;
    border-bottom: 1px solid #e2e7ee;
    box-sizing: border-box;
  }
  .row:nth-child(even) {
    background: #f7f9fc;
  }
  .row.sel {
    background: #fff7db;
    box-shadow: inset 3px 0 0 #f59e0b;
  }
  .c-sel {
    display: flex;
    justify-content: center;
  }
  .c-cell {
    text-align: center;
  }
  .c-cell.num {
    font-variant-numeric: tabular-nums;
  }
  .c-cell.arrow {
    font-size: 15px;
    color: #374151;
  }
  .c-cell.tag {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #4b5563;
  }
  .c-way a {
    color: #1d4ed8;
    text-decoration: none;
    font-weight: 600;
  }
  .c-len {
    font-variant-numeric: tabular-nums;
  }
  .c-len small {
    display: block;
    color: #9aa3af;
    font-size: 10px;
  }
  .c-name {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 3px 5px;
    min-width: 0;
  }
  .c-name .nm {
    white-space: normal;
  }
  /* speed cell: a box coloured by lane direction (the lane legend) with an inline
     maxspeed editor; blue ring = a staged (unsaved) edit */
  .c-speed {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 34px;
    border-radius: 4px;
  }
  .c-speed.dir-forward {
    background: #cdc;
  }
  .c-speed.dir-backward {
    background: #dcc;
  }
  .c-speed.dir-both {
    background: #ccccc5;
  }
  .c-speed.dir-none {
    background: #e5e7eb;
  }
  .c-speed.edited {
    outline: 2px solid #2563eb;
    outline-offset: -2px;
  }
  .spd {
    font: inherit;
    font-size: 12px;
    font-weight: 700;
    border: 1px solid #b8c2d1;
    border-radius: 4px;
    background: #fff;
    padding: 2px 1px;
    width: 100%;
    max-width: 64px;
  }
  .suggest {
    display: flex;
    gap: 3px;
    justify-content: center;
  }
  .suggest button {
    font: inherit;
    font-size: 11px;
    padding: 2px 4px;
    border: 1px solid #cbd6e4;
    border-radius: 4px;
    background: #fff;
    color: #6b7280;
    cursor: pointer;
  }
  .suggest button:hover {
    background: #eef4ff;
    color: #1d4ed8;
  }
  .c-tools {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 3px;
  }
  .c-tools .chip {
    font: inherit;
    font-size: 11px;
    line-height: 1;
    padding: 3px 5px;
    border: 1px solid #cbd6e4;
    border-radius: 4px;
    background: #fff;
    color: #1d4ed8;
    cursor: pointer;
    text-decoration: none;
    white-space: nowrap;
  }
  .c-tools .chip:hover {
    background: #eef4ff;
  }
  .c-tools .chip.act {
    color: #047857;
    border-color: #bfe3d4;
  }
  .c-tools .chip.act:hover {
    background: #ecfdf5;
  }
  .c-tools .div {
    width: 1px;
    align-self: stretch;
    background: #dde3ec;
    margin: 0 1px;
  }

  /* segment picked from the map: a sheet row, or a ported .label in full-lane mode */
  .row.picked {
    outline: 2px solid #e6194b;
    outline-offset: -2px;
    background: #ffe3ea;
  }
  .diagram :global(.label.picked) {
    outline: 2px solid #e6194b;
    outline-offset: 1px;
    background: #ffe3ea;
  }
</style>
