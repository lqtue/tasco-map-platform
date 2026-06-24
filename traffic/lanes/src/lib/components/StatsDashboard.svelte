<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { WayStat, RelationMeta, Criterion, Intersection } from '$lib/osm/types';

  let {
    stats = [],
    rawLengthKm = 0,
    officialKm = null,
    meta = null,
    intersections = [],
    intersectionsRan = false,
    actions
  }: {
    stats: WayStat[];
    rawLengthKm: number;
    officialKm: number | null;
    meta: RelationMeta | null;
    intersections: Intersection[];
    intersectionsRan: boolean;
    actions?: Snippet;
  } = $props();

  const MAJOR = new Set([
    'motorway', 'motorway_link', 'trunk', 'trunk_link',
    'primary', 'primary_link', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link'
  ]);
  const majorCount = $derived(
    intersections.filter((x) => x.roads.some((r) => MAJOR.has(r.highway))).length
  );

  // labels + order for the coverage criteria
  // meaningful completeness criteria (name/ref/oneway dropped — not survey gaps)
  const CRITERIA: { key: Criterion; label: string }[] = [
    { key: 'maxspeed', label: 'Maxspeed' },
    { key: 'lanes', label: 'Lane count' },
    { key: 'turn', label: 'Turn lanes' },
    { key: 'surface', label: 'Surface' },
    { key: 'lit', label: 'Lit' },
    { key: 'width', label: 'Width' },
    { key: 'shoulder', label: 'Shoulder' },
    { key: 'sidewalk', label: 'Sidewalk' },
    { key: 'structure', label: 'Bridge/Tunnel' },
    { key: 'access', label: 'Access' }
  ];

  const totalM = $derived(stats.reduce((s, w) => s + w.length, 0));

  // decoupled estimate: non-oneway counted fully, oneway halved (dual-carriageway heuristic)
  const decoupledKm = $derived(
    stats.reduce((s, w) => s + (w.oneway ? w.length / 2 : w.length), 0) / 1000
  );

  // length-weighted coverage per criterion
  const coverage = $derived(
    CRITERIA.map(({ key, label }) => {
      const covered = stats.reduce((s, w) => s + (w.present[key] ? w.length : 0), 0);
      const missingM = totalM - covered;
      const missingWays = stats.filter((w) => !w.present[key]).length;
      return {
        key,
        label,
        pct: totalM > 0 ? (covered / totalM) * 100 : 0,
        missingKm: missingM / 1000,
        missingWays
      };
    })
  );

  // distribution of numeric maxspeeds (km of road at each value)
  const speedDist = $derived(() => {
    const m = new Map<number, number>();
    for (const w of stats) if (w.maxspeed != null) m.set(w.maxspeed, (m.get(w.maxspeed) || 0) + w.length);
    return [...m.entries()].sort((a, b) => a[0] - b[0]).map(([v, len]) => ({ v, km: len / 1000 }));
  });

  function barColor(pct: number): string {
    if (pct >= 90) return '#2e7d32';
    if (pct >= 60) return '#f9a825';
    return '#c62828';
  }
  // length-vs-official: both far-under and far-over are discrepancies worth a look
  function covColor(pct: number): string {
    if (pct >= 90 && pct <= 110) return '#2e7d32';
    if (pct >= 70 && pct <= 130) return '#f9a825';
    return '#c62828';
  }

  // headline 1: overall attribute completeness = mean of the length-weighted criteria
  const overallPct = $derived(
    coverage.length ? coverage.reduce((s, c) => s + c.pct, 0) / coverage.length : 0
  );
  // headline 2: how much of the real road is mapped at all (decoupled to match official)
  const lengthCovPct = $derived(
    officialKm != null && officialKm > 0 ? (decoupledKm / officialKm) * 100 : null
  );
  // gaps to fix, worst first
  const ranked = $derived([...coverage].sort((a, b) => a.pct - b.pct));
</script>

<section class="module">
  <header>
    <h2>{meta?.ref || meta?.name || 'Road'} — completeness</h2>
    <span class="summary-hint">
      <b style={`color:${barColor(overallPct)}`}>{overallPct.toFixed(0)}%</b> tagged{#if lengthCovPct != null}
        · <b style={`color:${covColor(lengthCovPct)}`}>{lengthCovPct.toFixed(0)}%</b> vs official{/if}
    </span>
  </header>

  <div class="toolbar">{@render actions?.()}</div>

  <!-- two headline scores: the two questions a QA asks -->
  <div class="scores">
    <div class="score">
      <span class="big" style={`color:${barColor(overallPct)}`}>{overallPct.toFixed(0)}%</span>
      <span class="lbl">attributes tagged</span>
      <span class="hint">mean coverage across {coverage.length} fields, weighted by length</span>
    </div>
    <div class="score">
      {#if lengthCovPct != null}
        <span class="big" style={`color:${covColor(lengthCovPct)}`}>{lengthCovPct.toFixed(0)}%</span>
        <span class="lbl">length vs official</span>
        <span class="hint">~{decoupledKm.toFixed(1)} km in OSM vs {officialKm!.toFixed(1)} km official</span>
      {:else}
        <span class="big muted">—</span>
        <span class="lbl">length vs official</span>
        <span class="hint">no official length (Wikidata)</span>
      {/if}
    </div>
    <div class="meta-stats">
      <div><b>{rawLengthKm.toFixed(1)}</b> km in OSM</div>
      <div><b>{stats.length}</b> ways</div>
      {#if intersectionsRan}
        <div title="nodes shared with a crossing highway"><b>{intersections.length}</b> intersections ({majorCount} major)</div>
      {:else}
        <div class="muted-stat">intersections not checked</div>
      {/if}
    </div>
  </div>

  <!-- gaps to fix, worst first -->
  <div class="bars">
    {#each ranked as c (c.key)}
      <div class="bar" title={`${c.missingWays} ways · ${c.missingKm.toFixed(1)} km missing`}>
        <span class="blabel">{c.label}</span>
        <div class="track"><div class="fill" style={`width:${c.pct}%;background:${barColor(c.pct)}`}></div></div>
        <span class="bpct">{c.pct.toFixed(0)}%</span>
      </div>
    {/each}
  </div>

  <!-- details: sanity checks, not triage drivers -->
  <details class="details-disc">
    <summary class="btn">Details</summary>
    <div class="details">
      {#if speedDist().length}
        <div class="speeds">
          <span class="ctx">Maxspeed distribution</span>
          {#each speedDist() as s (s.v)}
            <span class="chip"><b>{Math.round(s.v)} km/h</b> · {s.km.toFixed(1)} km</span>
          {/each}
        </div>
      {/if}
      <p class="note">"length vs official" counts oneway ways as half (assumed dual carriageway); not geometry-paired. Over 100% usually means the relation covers more than the official figure.</p>
    </div>
  </details>
</section>

<style>
  .toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 8px;
  }
  .toolbar:empty {
    display: none;
  }
  .scores {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 24px;
    margin-bottom: 12px;
  }
  .score {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
    column-gap: 8px;
    align-items: baseline;
  }
  .score .big {
    grid-row: 1 / 3;
    font-size: 28px;
    font-weight: 800;
    line-height: 0.9;
  }
  .score .big.muted {
    color: #cbd2dc;
  }
  .score .lbl {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    align-self: end;
  }
  .score .hint {
    font-size: 11px;
    color: #9ca3af;
  }
  .meta-stats {
    margin-left: auto;
    font-size: 12px;
    color: #6b7280;
    text-align: right;
    line-height: 1.5;
  }
  .meta-stats b {
    color: #374151;
  }
  .muted-stat {
    color: #b6bcc6;
    font-style: italic;
  }

  .bars {
    display: grid;
    gap: 5px;
  }
  .bar {
    display: grid;
    grid-template-columns: 110px 1fr 38px;
    align-items: center;
    gap: 10px;
  }
  .blabel {
    font-size: 12px;
    color: #4b5563;
  }
  .bpct {
    font-size: 12px;
    font-weight: 700;
    text-align: right;
    color: #374151;
  }
  .track {
    height: 8px;
    border-radius: 4px;
    background: #eceff3;
    overflow: hidden;
  }
  .fill {
    height: 100%;
  }

  .details-disc {
    margin-top: 14px;
  }
  .details {
    margin-top: 10px;
    padding-top: 12px;
    border-top: 1px solid #eef1f5;
  }
  .speeds {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }
  .ctx {
    font-size: 12px;
    font-weight: 600;
    color: #4b5563;
  }
  .chip {
    background: #eef2ff;
    border: 1px solid #dbe2f5;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 12px;
    color: #4b5563;
  }
  .chip b {
    color: #1f2937;
  }
  .note {
    font-size: 11px;
    color: #9ca3af;
    margin: 10px 0 0;
    line-height: 1.4;
  }
</style>
