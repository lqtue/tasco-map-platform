<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';

  type Mode = 'coverage' | 'speed' | 'fresh';
  let mode = $state<Mode>('coverage');
  let snapshot = $state('');
  let status = $state('Loading national network…');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let L: any, map: any, layer: any;

  const STALE = 730;
  const freshHue = (d: number) => `hsl(${Math.round(120 * (1 - Math.min(d, STALE) / STALE))} 70% 45%)`;
  // speed value -> colour ramp (slow purple → fast red)
  function speedColor(ms: number) {
    if (ms <= 0) return '#d1d5db'; // no/unknown maxspeed
    if (ms <= 40) return '#7e22ce';
    if (ms <= 60) return '#2563eb';
    if (ms <= 80) return '#0891b2';
    if (ms <= 100) return '#16a34a';
    if (ms <= 120) return '#ca8a04';
    return '#dc2626';
  }
  function colorFor(p: { ms: number; age: number }) {
    if (mode === 'coverage') return p.ms > 0 ? '#2563eb' : '#e6194b';
    if (mode === 'speed') return speedColor(p.ms);
    return freshHue(p.age);
  }
  const style = (f: { properties: { ms: number; age: number } }) => ({
    color: colorFor(f.properties),
    weight: 2,
    opacity: 0.85
  });

  // legend entries per mode
  const LEGENDS: Record<Mode, [string, string][]> = {
    coverage: [
      ['#2563eb', 'has maxspeed'],
      ['#e6194b', 'missing — worklist']
    ],
    speed: [
      ['#7e22ce', '≤40'],
      ['#2563eb', '50–60'],
      ['#0891b2', '70–80'],
      ['#16a34a', '90–100'],
      ['#ca8a04', '110–120'],
      ['#dc2626', '>120'],
      ['#d1d5db', 'none']
    ],
    fresh: [
      [freshHue(0), 'fresh'],
      [freshHue(365), '1 yr'],
      [freshHue(STALE), 'stale ≥2 yr']
    ]
  };

  onMount(async () => {
    // @ts-expect-error leaflet ships no bundled types (same as MapView.svelte)
    L = (await import('leaflet')).default;
    await import('leaflet/dist/leaflet.css');
    map = L.map('natmap', { preferCanvas: true, maxZoom: 18 }).setView([16.0, 107.5], 6);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: 'Map © <a href="https://www.openstreetmap.org">OpenStreetMap</a>'
    }).addTo(map);
    try {
      const gj = await fetch(`${base}/data/national_roads.geojson`).then((r) => r.json());
      snapshot = gj.snapshot ?? '';
      layer = L.geoJSON(gj, {
        style,
        onEachFeature: (feat: { properties: { ref: string; ms: number; age: number } }, lyr: any) => {
          const p = feat.properties;
          const spd = p.ms > 0 ? `${p.ms} km/h` : p.ms === -1 ? 'present (non-numeric)' : 'missing';
          lyr.bindPopup(
            `<b>${p.ref}</b><br>maxspeed: ${spd}<br>last edit: ${p.age} d ago` +
              `<br><a href="${base}/editor?ref=${encodeURIComponent(p.ref)}" target="_blank" rel="noopener">Open in editor →</a>`
          );
        }
      }).addTo(map);
      status = `${gj.features.length.toLocaleString()} segments · QL + CT`;
    } catch (e) {
      status = 'Failed to load: ' + (e as Error).message;
    }
  });

  // recolor in place when the mode changes (no reload)
  $effect(() => {
    void mode;
    layer?.setStyle(style);
  });
</script>

<svelte:head><title>TASCO Road Atlas — national map</title></svelte:head>

<div class="head">
  <div class="modes">
    <span class="ttl">Colour by</span>
    <label><input type="radio" name="mode" value="coverage" bind:group={mode} /> maxspeed coverage</label>
    <label><input type="radio" name="mode" value="speed" bind:group={mode} /> speed value</label>
    <label><input type="radio" name="mode" value="fresh" bind:group={mode} /> edit freshness</label>
  </div>
  <div class="legend">
    {#each LEGENDS[mode] as [c, lbl] (lbl)}
      <span class="lg"><i style:background={c}></i>{lbl}</span>
    {/each}
  </div>
</div>
<p class="status">{status}{#if snapshot} · OSM snapshot {snapshot}{/if}</p>

<div id="natmap"></div>

<style>
  .head {
    display: flex;
    align-items: center;
    gap: 24px;
    flex-wrap: wrap;
    margin-bottom: 6px;
  }
  .modes {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 13px;
  }
  .ttl {
    font-weight: 600;
    color: #374151;
  }
  .modes label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #4b5563;
  }
  .legend {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    font-size: 12px;
    color: #6b7280;
  }
  .lg {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .lg i {
    width: 16px;
    height: 4px;
    border-radius: 2px;
    display: inline-block;
  }
  .status {
    font-size: 12px;
    color: #9aa3af;
    margin: 0 0 8px;
  }
  #natmap {
    width: 100%;
    height: calc(100vh - 150px);
    min-height: 420px;
    border: 1px solid #ccc;
    border-radius: 6px;
  }
</style>
