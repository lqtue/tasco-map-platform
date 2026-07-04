<script lang="ts">
  import { onMount } from 'svelte';
  import type { WayGeom } from '$lib/osm/types';
  import { fetchSpeedSigns, tileCount, type Bbox } from '$lib/osm/mapillary';

  // clicking a segment on the map tells the page which way to show in the diagram
  let { onpick }: { onpick?: (id: number) => void } = $props();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let L: any;
  let map: any;
  let roadLayer: any; // every segment polyline = the whole road
  let highlight: any; // overlay polyline for the focused segment
  let pairLine: any; // opposing carriageway of the focused segment
  let beginPt: any; // begin marker for the focused segment
  let crossLayer: any; // crossing markers for the whole road
  let allGeoms: Record<number, WayGeom> = {}; // so focus() can find a segment's pair
  let mapEl: HTMLDivElement;
  let layersControl: any;
  let baseLayers: any[] = []; // built-in bases, so a custom layer can replace them
  let customLayer: any;
  let geomOpacity = $state(0.85); // road geometry line opacity (slider)
  let customUrl = $state('');

  // Mapillary already-detected speed-sign overlay (evidence layer for editing)
  let signLayer: any;
  let signsOn = $state(false);
  let mlyToken = $state(''); // Mapillary client token (MLY|…), kept in localStorage
  let signStatus = $state('');
  let signTimer: any;

  // overzoom past a source's native max instead of showing blank/grey tiles
  const TILE_OPTS = { maxNativeZoom: 19, maxZoom: 22 };

  function applyOpacity() {
    roadLayer?.setStyle({ opacity: geomOpacity });
  }

  // add (or replace) a custom XYZ tile source and switch to it. {z}/{x}/{y} template.
  function addCustom() {
    const url = customUrl.trim();
    // need all three placeholders, in any order (e.g. Google: ?x={x}&y={y}&z={z})
    if (!map || !['{z}', '{x}', '{y}'].every((t) => url.includes(t))) return;
    if (customLayer) {
      map.removeLayer(customLayer);
      layersControl.removeLayer(customLayer);
    }
    customLayer = L.tileLayer(url, { attribution: 'Custom XYZ', ...TILE_OPTS });
    layersControl.addBaseLayer(customLayer, 'Custom');
    for (const l of baseLayers) map.removeLayer(l);
    customLayer.addTo(map);
  }

  onMount(async () => {
    L = (await import('leaflet')).default;
    await import('leaflet/dist/leaflet.css');
    map = L.map(mapEl, { maxZoom: 22 }).setView([16.0, 107.5], 5); // Vietnam
    const osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: 'Map © <a href="https://www.openstreetmap.org">OpenStreetMap</a>',
      ...TILE_OPTS
    }).addTo(map);
    // Google satellite serves imagery to a higher native zoom than Esri (which
    // went blank past z19), so close-up sign checking still shows tiles.
    const sat = L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
      attribution: 'Imagery © Google',
      maxNativeZoom: 20,
      maxZoom: 22
    });
    baseLayers = [osm, sat];
    layersControl = L.control.layers({ OSM: osm, Satellite: sat }, {}, { position: 'topright' }).addTo(map);
    mlyToken = localStorage.getItem('mapillary_token') ?? '';
    // pan/zoom (incl. showRoad's fitBounds) reloads the sign overlay for the new view
    map.on('moveend', () => {
      if (!signsOn) return;
      clearTimeout(signTimer);
      signTimer = setTimeout(loadSigns, 400);
    });
    // the map sits in a CSS-grid column; recompute size once layout settles
    setTimeout(() => map.invalidateSize(), 0);
  });

  // a Mapillary speed-sign marker: a red-ringed circle with the km/h value
  function signMarker(s: { lat: number; lng: number; value: number | null; last_seen: string | null }) {
    const label = s.value ?? '?';
    const icon = L.divIcon({
      className: '',
      html: `<div class="mly-sign">${label}</div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 13]
    });
    const seen = s.last_seen ? s.last_seen.slice(0, 10) : 'unknown';
    const mly = `https://www.mapillary.com/app/?lat=${s.lat.toFixed(6)}&lng=${s.lng.toFixed(6)}&z=18`;
    return L.marker([s.lat, s.lng], { icon }).bindPopup(
      `<b>${label} km/h</b> · Mapillary<br>last seen ${seen}<br>` +
        `<a href="${mly}" target="_blank" rel="noopener">📷 view here</a>`
    );
  }

  // fetch + draw the detected speed signs in the current viewport
  async function loadSigns() {
    if (!map || !signsOn) return;
    const token = mlyToken.trim();
    if (!token) {
      signStatus = 'paste a Mapillary token (MLY|…)';
      return;
    }
    const b = map.getBounds();
    const bbox: Bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
    if (tileCount(bbox) > 64) {
      signStatus = 'zoom in to load signs';
      return;
    }
    signStatus = 'loading…';
    try {
      const signs = await fetchSpeedSigns(bbox, token);
      if (signLayer) map.removeLayer(signLayer);
      signLayer = L.layerGroup(signs.map(signMarker)).addTo(map);
      signStatus = `${signs.length} sign${signs.length === 1 ? '' : 's'}`;
    } catch (e) {
      signStatus = (e as Error).message || 'fetch failed';
    }
  }

  function onToggleSigns() {
    if (signsOn) {
      localStorage.setItem('mapillary_token', mlyToken.trim());
      loadSigns();
    } else if (signLayer) {
      map.removeLayer(signLayer);
      signLayer = null;
      signStatus = '';
    }
  }

  // circle marker for the begin point (avoids Leaflet's missing default icon PNG)
  function beginMarker(latlng: [number, number]) {
    return L.circleMarker(latlng, {
      radius: 6,
      color: '#1d4ed8',
      weight: 2,
      fillColor: '#3b82f6',
      fillOpacity: 1
    }).addTo(map);
  }

  function crossingMarker(x: { lat: number; lon: number; label: string }) {
    const m = `https://www.mapillary.com/app/?lat=${x.lat.toFixed(6)}&lng=${x.lon.toFixed(6)}&z=17`;
    return L.circleMarker([x.lat, x.lon], {
      radius: 6,
      color: '#b45309',
      weight: 2,
      fillColor: '#f59e0b',
      fillOpacity: 1
    })
      .bindTooltip(x.label)
      .bindPopup(`<b>${x.label}</b><br><a href="${m}" target="_blank" rel="noopener">📷 Mapillary here</a>`);
  }

  // imperative API used by the page (via bind:this)

  // draw the whole road and fit it in the viewport (called after a search)
  export function showRoad(geoms: Record<number, WayGeom>) {
    if (!map) return;
    allGeoms = geoms;
    for (const layer of [roadLayer, highlight, pairLine, beginPt, crossLayer]) if (layer) map.removeLayer(layer);
    highlight = pairLine = beginPt = null;
    const lines: any[] = [];
    const crossings: any[] = [];
    for (const id in geoms) {
      const g = geoms[id];
      if (g.line?.length) {
        const pl = L.polyline(g.line, { color: '#3b82f6', weight: 3, opacity: geomOpacity });
        pl.on('click', () => {
          focus(g, false); // mark it on the map
          onpick?.(Number(id)); // and surface it in the diagram
        });
        lines.push(pl);
      }
      for (const x of g.crossings ?? []) if (x.lat != null && x.lon != null) crossings.push(crossingMarker(x));
    }
    roadLayer = L.featureGroup(lines).addTo(map);
    crossLayer = L.layerGroup(crossings).addTo(map);
    if (lines.length) map.fitBounds(roadLayer.getBounds(), { padding: [30, 30] });
  }

  // overlay one segment on top of the road; fit the view to it only when `fit`
  function focus(c: WayGeom | undefined, fit: boolean) {
    if (!c || !map) return;
    for (const layer of [highlight, pairLine, beginPt]) if (layer) map.removeLayer(layer);
    pairLine = null;
    highlight = L.polyline(c.line, { color: '#e6194b', weight: 6, opacity: 1 }).addTo(map);
    beginPt = beginMarker(c.begin);
    // if this segment is one carriageway of a divided road, show the other one too
    const mate = c.pairId != null ? allGeoms[c.pairId] : undefined;
    if (mate?.line?.length)
      pairLine = L.polyline(mate.line, {
        color: '#16a34a',
        weight: 6,
        opacity: 0.9,
        dashArray: '6,8'
      }).addTo(map);
    if (fit) {
      const grp = L.featureGroup([highlight, pairLine].filter(Boolean));
      map.fitBounds(grp.getBounds(), { padding: [40, 40] });
    }
  }
  export function highlightSeg(c: WayGeom | undefined) {
    focus(c, false); // hover: highlight only, don't move the map
  }
  export function zoom(c: WayGeom | undefined) {
    focus(c, true); // (Z) button: highlight + zoom to it
  }
  export function resize() {
    map?.invalidateSize();
  }
</script>

<div class="mapwrap">
  <div class="map" bind:this={mapEl}></div>
  <details class="map-opts">
    <summary class="btn">Map options</summary>
    <div class="hint">
      <label class="opacity">Road opacity {Math.round(geomOpacity * 100)}%
        <input type="range" min="0.1" max="1" step="0.05" bind:value={geomOpacity} oninput={applyOpacity} />
      </label>
      <label class="custom">XYZ
        <input
          type="text"
          placeholder={'https://…/{z}/{x}/{y}.png'}
          bind:value={customUrl}
          onkeydown={(e) => e.key === 'Enter' && addCustom()}
        />
      </label>
      <button class="btn" onclick={addCustom}>Add</button>
      <label class="signs">
        <input type="checkbox" bind:checked={signsOn} onchange={onToggleSigns} /> Mapillary speed signs
      </label>
      <input
        class="tok"
        type="password"
        placeholder="MLY|token"
        bind:value={mlyToken}
        onblur={() => signsOn && (localStorage.setItem('mapillary_token', mlyToken.trim()), loadSigns())}
      />
      {#if signStatus}<span class="sstat">{signStatus}</span>{/if}
    </div>
  </details>
</div>

<style>
  .mapwrap {
    position: sticky;
    top: calc(var(--head-h, 90px) + 8px); /* clear the page's sticky search header */
  }
  .map {
    width: 100%;
    height: calc(100vh - var(--head-h, 90px) - 16px);
    min-height: 400px;
    border: 1px solid #ccc;
    border-radius: 6px;
  }
  .map-opts {
    margin: 6px 2px 0;
  }
  .hint {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    font-size: 11px;
    color: #888;
    margin: 8px 0 0;
  }
  .opacity,
  .custom {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .custom {
    flex: 1;
    min-width: 140px;
  }
  .custom input {
    flex: 1;
    min-width: 0;
    font: inherit;
    font-size: 11px;
    padding: 3px 6px;
    border: 1px solid #cbd2dc;
    border-radius: 4px;
  }
  .hint .btn {
    font-size: 11px;
    padding: 3px 10px;
  }
  .signs {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .tok {
    width: 120px;
    font: inherit;
    font-size: 11px;
    padding: 3px 6px;
    border: 1px solid #cbd2dc;
    border-radius: 4px;
  }
  .sstat {
    color: #6b7280;
  }
  /* Leaflet divIcon is created at runtime outside the scoped DOM → must be global */
  :global(.mly-sign) {
    width: 26px;
    height: 26px;
    border: 3px solid #e11d48;
    border-radius: 50%;
    background: #fff;
    color: #111;
    font: 700 11px/1 sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
  }
</style>
