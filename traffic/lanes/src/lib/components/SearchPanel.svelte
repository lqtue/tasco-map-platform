<script lang="ts">
  import { wayQuery, relQuery, relNameQuery, relRefQuery } from '$lib/osm/visualizer';
  import { PRESETS, DEFAULT_PRESET } from '$lib/osm/columns';
  import type { Options, SearchRequest } from '$lib/osm/types';

  let {
    country = $bindable('vn'),
    showLanes = $bindable(false),
    columns = $bindable<string[]>([...PRESETS[DEFAULT_PRESET]]),
    active = $bindable<string | null>(null), // which panel (config/completeness/legend/columns/profile) is open
    hasResult = false,
    totalStartPoints = 0,
    loading = false,
    onsearch,
    controls
  }: {
    country: string;
    showLanes: boolean;
    columns: string[];
    active: string | null;
    hasResult: boolean;
    totalStartPoints: number;
    loading: boolean;
    onsearch: (r: SearchRequest) => void;
    controls?: import('svelte').Snippet; // extra buttons (Hide map / Help) rendered in the strip
  } = $props();

  // result-view panels offered once there's data (config is always available)
  const VIEWS = [
    ['completeness', 'Completeness'],
    ['legend', 'Legend'],
    ['columns', 'Columns'],
    ['profile', 'Speed profile']
  ] as const;
  const toggle = (k: string) => (active = active === k ? null : k);

  // --- search by: one selector + one input, instead of four rows ----------
  const SEARCH_BY = [
    { key: 'relref', label: 'Relation by ref', placeholder: 'QL.51', build: relRefQuery },
    { key: 'relname', label: 'Relation by name', placeholder: 'Quốc lộ 51', build: relNameQuery },
    { key: 'relid', label: 'Relation by id', placeholder: '123456', build: relQuery },
    { key: 'wayid', label: 'Way by id', placeholder: '123456', build: wayQuery }
  ] as const;

  let searchBy = $state<(typeof SEARCH_BY)[number]['key']>('relname');
  let term = $state('Quốc lộ 51');
  const current = $derived(SEARCH_BY.find((s) => s.key === searchBy)!);

  // --- configuration toggles + their explanations -------------------------
  const CONFIG = [
    { key: 'usePlacement', label: 'Use placement', help: 'Use the placement tag to position lanes more naturally on the carriageway.' },
    { key: 'adjacent', label: 'Use adjacent ways', help: "Also draw ways that join at each segment's end node." },
    { key: 'lanewidth', label: 'Use lane width', help: 'Read lane width from the width tag instead of a fixed size.' },
    { key: 'usenodes', label: 'Use tags on nodes', help: 'Show node tags (signals, stop, crossing…) along the way.' },
    { key: 'extendway', label: 'Include ways before & after', help: 'Add arrows to step to the way before and after this one.' },
    { key: 'intersections', label: 'Detect intersections', help: 'Find roads crossing this one (one extra Overpass query).' }
  ] as const;

  let cfg = $state<Record<string, boolean>>({
    usePlacement: false,
    adjacent: false,
    lanewidth: false,
    usenodes: false,
    extendway: false,
    intersections: false
  });
  let start = $state(1);

  function go() {
    if (loading) return;
    const opts: Options = { country, ...cfg } as Options;
    onsearch({ query: current.build(term.trim()), start: Number(start) || 1, opts });
  }
</script>

<details class="module" open>
  <summary>
    <h2>Search</h2>
    {#if term.trim()}<span class="summary-hint">{current.label}: {term.trim()}</span>{/if}
  </summary>

  <div class="row search-row">
    <select bind:value={searchBy} title="Search by">
      {#each SEARCH_BY as s (s.key)}<option value={s.key}>{s.label}</option>{/each}
    </select>
    <input
      type="text"
      bind:value={term}
      placeholder={current.placeholder}
      onkeydown={(e) => e.key === 'Enter' && go()}
      style="flex:1;min-width:140px"
    />
    <button class="btn btn-primary" disabled={loading} onclick={go}>
      {loading ? 'Searching…' : 'Search'}
    </button>
  </div>

  <!-- one button strip: Configuration + the result-view panel toggles (one open at a time) -->
  <div class="ctl-row">
    <button class="btn" class:on={active === 'config'} aria-pressed={active === 'config'} onclick={() => toggle('config')}>Configuration</button>
    {#if hasResult}
      <span class="sep"></span>
      {#each VIEWS as [k, label] (k)}
        <button class="btn" class:on={active === k} aria-pressed={active === k} onclick={() => toggle(k)}>{label}</button>
      {/each}
    {/if}
    {#if controls}
      <span class="ctl-spacer"></span>
      {@render controls()}
    {/if}
  </div>

  {#if active === 'config'}
    <div class="config-grid">
      {#each CONFIG as c (c.key)}
        <div class="opt">
          <label><input type="checkbox" bind:checked={cfg[c.key]} /> {c.label}</label>
          <p class="opt-help">{c.help}</p>
        </div>
      {/each}
      <div class="opt">
        <label><input type="checkbox" bind:checked={showLanes} /> Show full lanes</label>
        <p class="opt-help">Off (default): the maxspeed editing sheet (one lane per segment). On: draw every lane.</p>
      </div>
      <div class="opt">
        <label title={`Which chain end to begin drawing from (${totalStartPoints} found).`}>Start at end number <input type="text" bind:value={start} style="width:42px" /></label>
      </div>
      <div class="opt">
        <label title="Country (route-shield colours)">Country
          <select bind:value={country}>
            <option value="vn">vn</option>
            <option value="de">de</option>
            <option value="be">be</option>
          </select>
        </label>
      </div>
    </div>
  {/if}
</details>

<style>
  .search-row {
    margin-bottom: 8px;
  }
  .ctl-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }
  .ctl-row .sep {
    width: 1px;
    align-self: stretch;
    background: #dde3ec;
    margin: 2px 4px;
  }
  .ctl-row .ctl-spacer {
    margin-left: auto; /* push Hide map / Help to the right end of the strip */
  }
  .config-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 6px 16px;
    margin-top: 10px;
  }
  .opt label {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .opt-help {
    margin: 2px 0 0 22px;
    font-size: 0.8em;
    opacity: 0.7;
    line-height: 1.3;
  }
</style>
