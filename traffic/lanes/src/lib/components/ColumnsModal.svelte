<script lang="ts">
  import { PRESETS, colDef } from '$lib/osm/columns';

  // allKeys = the full column universe (computed columns + every raw tag in the data)
  let {
    allKeys = [],
    columns = $bindable<string[]>([])
  }: { allKeys: string[]; columns: string[] } = $props();

  const has = (k: string) => columns.includes(k);
  function toggle(k: string) {
    columns = has(k) ? columns.filter((c) => c !== k) : [...columns, k];
  }
  function applyPreset(p: string) {
    columns = [...PRESETS[p]];
  }
  function setAll(on: boolean) {
    columns = on ? [...allKeys] : [];
  }
</script>

<div class="cols-panel">
  <div class="bar">
    <span class="lbl">Presets:</span>
    {#each Object.keys(PRESETS) as p (p)}
      <button class="btn" onclick={() => applyPreset(p)}>{p}</button>
    {/each}
    <span class="count">{columns.length}/{allKeys.length}</span>
    <button class="btn" onclick={() => setAll(true)}>All</button>
    <button class="btn" onclick={() => setAll(false)}>None</button>
  </div>
  <div class="fields">
    {#each allKeys as k (k)}
      <label class="field"><input type="checkbox" checked={has(k)} onchange={() => toggle(k)} /> {colDef(k).label}</label>
    {/each}
  </div>
</div>

<style>
  .bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-bottom: 10px;
  }
  .lbl {
    font-size: 12px;
    color: #6b7280;
  }
  .count {
    font-size: 12px;
    color: #6b7280;
    margin-left: auto;
  }
  .fields {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 4px 12px;
    max-height: 280px;
    overflow: auto;
    padding: 8px;
    border: 1px solid #eef1f5;
    border-radius: 6px;
    background: #fafbfd;
  }
  .field {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: #374151;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
