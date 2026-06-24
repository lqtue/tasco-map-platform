<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';

  // one route relation, as emitted by traffic/maxspeed/baseline/route_coverage.py
  type Route = {
    ref: string;
    name: string;
    km: number;
    centerline_km: number;
    maxspeed_km: number;
    pct_maxspeed: number;
    classes: string;
    n_ways: number;
    components: number;
  };
  // per-route maxspeed profile + edit freshness, from route_freshness.py
  type Fresh = { bins: [number, number][]; med_age: number }; // [maxspeed_code, age_days]

  let all = $state<Route[]>([]);
  let fresh = $state<Record<string, Fresh>>({});
  let snapshot = $state('');
  let err = $state('');
  let q = $state('');
  let nationalOnly = $state(true); // scope = quốc lộ (QL) + cao tốc (CT)
  let sortKey = $state<'missing' | 'centerline_km' | 'pct_maxspeed' | 'stale' | 'components' | 'ref'>('missing');
  let sortDir = $state<1 | -1>(-1);

  onMount(async () => {
    try {
      const [cov, fr] = await Promise.all([
        fetch(`${base}/data/route_coverage.json`).then((r) => r.json()),
        fetch(`${base}/data/route_freshness.json`).then((r) => r.json())
      ]);
      all = cov;
      fresh = fr.routes;
      snapshot = fr.snapshot;
    } catch (e) {
      err = (e as Error).message;
    }
  });

  const isNational = (ref: string) => /^(QL|CT)\b|^(QL|CT)\./i.test(ref);
  const missingKm = (r: Route) => r.centerline_km * (1 - r.pct_maxspeed / 100);
  const ageOf = (r: Route) => fresh[r.ref]?.med_age ?? Infinity; // untracked sorts last

  const rows = $derived.by(() => {
    const needle = q.trim().toLowerCase();
    const filtered = all.filter(
      (r) =>
        (!nationalOnly || isNational(r.ref)) &&
        (!needle || r.ref.toLowerCase().includes(needle) || (r.name || '').toLowerCase().includes(needle))
    );
    const val = (r: Route) =>
      sortKey === 'missing' ? missingKm(r) : sortKey === 'stale' ? ageOf(r) : sortKey === 'ref' ? 0 : r[sortKey];
    return filtered.sort((a, b) => {
      if (sortKey === 'ref') return sortDir * a.ref.localeCompare(b.ref);
      return sortDir * (val(a) - val(b));
    });
  });

  // headline stats over the current filter (centerline km, comparable to official road length)
  const totals = $derived.by(() => {
    const t = rows.reduce(
      (a, r) => {
        a.cl += r.centerline_km;
        a.miss += missingKm(r);
        return a;
      },
      { cl: 0, miss: 0 }
    );
    const pct = t.cl ? (1 - t.miss / t.cl) * 100 : 0;
    return { cl: t.cl, miss: t.miss, pct, n: rows.length };
  });

  // red (0%) -> green (100%) heat for a coverage percentage
  const heat = (pct: number) => `hsl(${Math.round(pct * 1.2)} 65% 42%)`;
  // fresh (0 days, green) -> stale (>=2yr, red); the profile-bar + freshness-cell color
  const STALE = 730;
  const freshHue = (days: number) => `hsl(${Math.round(120 * (1 - Math.min(days, STALE) / STALE))} 70% 42%)`;
  const fmt = (n: number) => n.toLocaleString('en', { maximumFractionDigits: 0 });
  const ageLabel = (d: number) =>
    !Number.isFinite(d) ? '—' : d >= 365 ? (d / 365).toFixed(1) + ' yr' : d >= 30 ? Math.round(d / 30) + ' mo' : d + ' d';
  // profile bar height: maxspeed value scaled into the 30-unit viewBox (min 2 for visibility)
  const SPARK_H = 30;
  const barH = (ms: number) => (ms > 0 ? Math.min(ms, 130) / 130 * (SPARK_H - 2) + 2 : 2);

  function sortBy(k: typeof sortKey) {
    if (sortKey === k) sortDir = (sortDir * -1) as 1 | -1;
    else {
      sortKey = k;
      sortDir = k === 'ref' ? 1 : -1;
    }
  }
  const arrow = (k: typeof sortKey) => (sortKey === k ? (sortDir === -1 ? ' ▼' : ' ▲') : '');
</script>

<svelte:head><title>TASCO Road Atlas — maxspeed coverage</title></svelte:head>

<h1>National road maxspeed coverage</h1>
<p class="sub">
  Per-route status from OSM route relations (<code>route_coverage.py</code> · <code>route_freshness.py</code>).
  Centerline km ≈ member km with divided carriageways halved — the figure to compare against official
  road-length stats. {#if snapshot}<span class="snap">OSM snapshot {snapshot}.</span>{/if}
</p>

{#if err}<p class="err">Couldn't load data: {err}</p>{/if}

<section class="cards">
  <div class="card">
    <div class="num">{fmt(totals.cl)}<span>km</span></div>
    <div class="lbl">Centerline length{nationalOnly ? ', QL + CT' : ', all routes'}</div>
  </div>
  <div class="card">
    <div class="num" style:color={heat(totals.pct)}>{totals.pct.toFixed(1)}<span>%</span></div>
    <div class="lbl">Carry a maxspeed tag</div>
  </div>
  <div class="card">
    <div class="num" style:color={heat(0)}>{fmt(totals.miss)}<span>km</span></div>
    <div class="lbl">Missing maxspeed — the worklist</div>
  </div>
  <div class="card">
    <div class="num">{totals.n}</div>
    <div class="lbl">Routes shown</div>
  </div>
</section>

<div class="bar">
  <input class="search" placeholder="filter by ref or name…" bind:value={q} />
  <label class="chk"><input type="checkbox" bind:checked={nationalOnly} /> National &amp; expressway only (QL / CT)</label>
  <span class="legend" title="Profile bar height = maxspeed value; colour = how recently that stretch was last edited in OSM">
    freshness
    <i style:background={freshHue(0)}></i>fresh
    <i style:background={freshHue(365)}></i>1yr
    <i style:background={freshHue(STALE)}></i>stale
    <i class="none"></i>no maxspeed
  </span>
</div>

<table>
  <thead>
    <tr>
      <th class="r" onclick={() => sortBy('ref')}>Ref{arrow('ref')}</th>
      <th>Name</th>
      <th class="num-h" onclick={() => sortBy('centerline_km')}>Centerline km{arrow('centerline_km')}</th>
      <th class="cov-h" onclick={() => sortBy('pct_maxspeed')}>Coverage{arrow('pct_maxspeed')}</th>
      <th class="num-h" onclick={() => sortBy('missing')}>Missing km{arrow('missing')}</th>
      <th>Speed profile · freshness</th>
      <th class="num-h" onclick={() => sortBy('stale')} title="Length-weighted median time since last edit">Edited{arrow('stale')}</th>
      <th class="num-h" onclick={() => sortBy('components')} title="Connected components: >1 = gaps / disjoint route">Gaps{arrow('components')}</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {#each rows as r (r.ref)}
      <tr>
        <td class="r"><span class="shield" class:ct={/^CT/i.test(r.ref)} title={r.classes}>{r.ref}</span></td>
        <td class="name" title={r.name}>{r.name || '—'}</td>
        <td class="n">{fmt(r.centerline_km)}</td>
        <td class="cov">
          <div class="track" title="{r.pct_maxspeed.toFixed(1)}% of member km carry maxspeed">
            <div class="fill" style:width="{r.pct_maxspeed}%" style:background={heat(r.pct_maxspeed)}></div>
          </div>
          <span class="pct" style:color={heat(r.pct_maxspeed)}>{r.pct_maxspeed.toFixed(0)}%</span>
        </td>
        <td class="n miss">{fmt(missingKm(r))}</td>
        <td class="prof">
          {#if fresh[r.ref]}
            {@const bins = fresh[r.ref].bins}
            <a class="sparklink" href={`${base}/editor?ref=${encodeURIComponent(r.ref)}`} title="Open {r.ref} in the editor">
              <svg class="spark" viewBox="0 0 {bins.length} {SPARK_H}" preserveAspectRatio="none"
                role="img" aria-label="speed profile coloured by edit freshness — open in editor">
                {#each bins as [ms, age], i (i)}
                  <rect x={i} width="1" y={SPARK_H - barH(ms)} height={barH(ms)}
                    fill={ms > 0 ? freshHue(age) : '#e2e6ec'} />
                {/each}
              </svg>
            </a>
          {/if}
        </td>
        <td class="n age" style:color={freshHue(ageOf(r))}>{ageLabel(ageOf(r))}</td>
        <td class="n" class:gap={r.components > 1}>{r.components}</td>
        <td class="r"><a class="open" href={`${base}/editor?ref=${encodeURIComponent(r.ref)}`}>Open →</a></td>
      </tr>
    {/each}
  </tbody>
</table>

{#if !rows.length && !err}<p class="sub">No routes match.</p>{/if}

<style>
  h1 {
    margin: 4px 0;
  }
  .sub {
    color: #6b7280;
    font-size: 13px;
    max-width: 80ch;
    margin: 0 0 14px;
  }
  .snap {
    color: #9aa3af;
  }
  .err {
    color: #b00;
    font-weight: 600;
  }
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }
  .card {
    border: 1px solid #e3e7ee;
    border-radius: 8px;
    padding: 12px 14px;
    background: #fafbfc;
  }
  .num {
    font-size: 28px;
    font-weight: 700;
    color: #1f2937;
    line-height: 1.1;
  }
  .num span {
    font-size: 14px;
    font-weight: 500;
    color: #9aa3af;
    margin-left: 3px;
  }
  .lbl {
    font-size: 12px;
    color: #6b7280;
    margin-top: 4px;
  }
  .bar {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 10px;
  }
  .search {
    font: inherit;
    padding: 5px 10px;
    border: 1px solid #cbd2dc;
    border-radius: 5px;
    min-width: 220px;
  }
  .chk {
    font-size: 13px;
    color: #4b5563;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .legend {
    font-size: 12px;
    color: #6b7280;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .legend i {
    width: 14px;
    height: 11px;
    border-radius: 2px;
    display: inline-block;
  }
  .legend i.none {
    background: #e2e6ec;
    margin-left: 6px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
  }
  th,
  td {
    padding: 6px 10px;
    border-bottom: 1px solid #eef1f5;
    text-align: left;
  }
  thead th {
    position: sticky;
    top: 0;
    background: #fff;
    color: #374151;
    border-bottom: 2px solid #e3e7ee;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
  }
  th.num-h,
  th.cov-h {
    text-align: right;
  }
  .n {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .miss {
    font-weight: 600;
  }
  .age {
    font-weight: 600;
  }
  .gap {
    color: #b45309;
    font-weight: 700;
  }
  .name {
    max-width: 26ch;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  tr:hover td {
    background: #f6f9fe;
  }
  .shield {
    display: inline-block;
    background: #1a5fb4;
    color: #fff;
    font-weight: 700;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 3px;
    white-space: nowrap;
    cursor: help;
  }
  .shield.ct {
    background: #168039;
  }
  .cov {
    display: flex;
    align-items: center;
    gap: 8px;
    justify-content: flex-end;
  }
  .track {
    flex: 1;
    max-width: 120px;
    height: 9px;
    background: #fdecec;
    border-radius: 5px;
    overflow: hidden;
  }
  .fill {
    height: 100%;
  }
  .pct {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    min-width: 34px;
    text-align: right;
  }
  .prof {
    width: 170px;
  }
  .sparklink {
    display: block;
  }
  .spark {
    display: block;
    width: 170px;
    height: 30px;
  }
  .sparklink:hover .spark {
    outline: 1px solid #93b4e6;
    border-radius: 2px;
  }
  .open {
    color: #1a5fb4;
    text-decoration: none;
    font-weight: 600;
    white-space: nowrap;
  }
  .open:hover {
    text-decoration: underline;
  }
</style>
