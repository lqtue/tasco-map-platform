<script lang="ts">
  import type { ExportRow } from '$lib/osm/types';

  let { rows = [], name = 'osm-export' }: { rows: ExportRow[]; name?: string } = $props();

  let dialog: HTMLDialogElement;
  let format = $state<'csv' | 'json'>('csv');

  // union of all keys across rows, first-seen order (computed fields lead, tags follow)
  const columns = $derived.by(() => {
    const seen: string[] = [];
    for (const r of rows) for (const k of Object.keys(r)) if (!seen.includes(k)) seen.push(k);
    return seen;
  });

  // which columns to include; default every column on
  let picked = $state<Record<string, boolean>>({});
  $effect(() => {
    for (const c of columns) if (!(c in picked)) picked[c] = true;
  });
  const chosen = $derived(columns.filter((c) => picked[c]));

  function setAll(v: boolean) {
    for (const c of columns) picked[c] = v;
  }

  function csvCell(v: unknown): string {
    const s = v == null ? '' : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }

  function download() {
    if (!chosen.length) return;
    let blob: string, ext: string, mime: string;
    if (format === 'csv') {
      const lines = [chosen.map(csvCell).join(',')];
      for (const r of rows) lines.push(chosen.map((c) => csvCell(r[c])).join(','));
      blob = lines.join('\n');
      ext = 'csv';
      mime = 'text/csv';
    } else {
      blob = JSON.stringify(
        rows.map((r) => Object.fromEntries(chosen.map((c) => [c, r[c] ?? null]))),
        null,
        2
      );
      ext = 'json';
      mime = 'application/json';
    }
    const url = URL.createObjectURL(new Blob([blob], { type: mime }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name.replace(/[^\w.-]+/g, '_')}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
    dialog.close();
  }
</script>

<button class="btn" onclick={() => dialog.showModal()}>⬇ Export data</button>

<dialog bind:this={dialog} class="export-dialog">
  <header>
    <h2>Export {rows.length} ways</h2>
    <button class="btn close" onclick={() => dialog.close()} aria-label="Close">✕</button>
  </header>

  <div class="row toolbar">
    <label><input type="radio" bind:group={format} value="csv" /> CSV</label>
    <label><input type="radio" bind:group={format} value="json" /> JSON</label>
    <span class="sep">·</span>
    <span class="count">{chosen.length}/{columns.length} fields</span>
    <button class="btn" onclick={() => setAll(true)}>All</button>
    <button class="btn" onclick={() => setAll(false)}>None</button>
  </div>

  <div class="fields">
    {#each columns as c (c)}
      <label class="field"><input type="checkbox" bind:checked={picked[c]} /> {c}</label>
    {/each}
  </div>

  <footer>
    <button class="btn" onclick={() => dialog.close()}>Cancel</button>
    <button class="btn btn-primary" disabled={!chosen.length} onclick={download}>
      Download {format.toUpperCase()}
    </button>
  </footer>
</dialog>

<style>
  .export-dialog {
    width: min(640px, 92vw);
    border: 1px solid #d9dee6;
    border-radius: 10px;
    padding: 16px 18px;
    font-family: sans-serif;
  }
  .export-dialog::backdrop {
    background: rgba(17, 24, 39, 0.45);
  }
  .export-dialog header {
    display: flex;
    align-items: center;
    margin-bottom: 12px;
  }
  .export-dialog header h2 {
    margin: 0;
    font-size: 16px;
    flex: 1;
  }
  .close {
    padding: 2px 8px;
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
  }
  .toolbar label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
  }
  .sep {
    color: #cbd2dc;
  }
  .count {
    font-size: 12px;
    color: #6b7280;
    margin-right: auto;
  }
  .fields {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 4px 12px;
    max-height: 320px;
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
  footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 14px;
  }
</style>
