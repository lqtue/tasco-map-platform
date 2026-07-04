// Live fetch of already-detected speed-limit signs from Mapillary's free Map
// Features Graph API — the browser twin of traffic/signs/mapillary_signs.py.
// Used as an evidence overlay in the editor map: the editor navigates a road,
// loads the signs in view, and eyeballs them against the staged maxspeed edits.
//
// Two hard API limits shape this (same as the python): the per-request bbox must
// be tiny (dense tiles 500 above ~0.01 sq-deg), and a long object_values list
// also 500s — so we tile the bbox at TILE_DEG and request only the g1 speed
// class. Map Features has no server-side date filter; last_seen is the freshness.

const API = 'https://graph.mapillary.com/map_features';
const FIELDS = 'id,object_value,geometry,first_seen_at,last_seen_at';
const SPEEDS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 120];
const OBJECT_VALUES = SPEEDS.map((s) => `regulatory--maximum-speed-limit-${s}--g1`).join(',');
const SPEED_RE = /maximum-speed-limit-(\d+)/;
const TILE_DEG = 0.02; // ~2.2 km; dense urban tiles 500 above this
const MAX_TILES = 64; // ponytail: hard cap on live requests; UI gates the viewport so this is rarely hit

export interface SignPoint {
  lat: number;
  lng: number;
  value: number | null;
  sign_id: string;
  last_seen: string | null;
}

export type Bbox = [number, number, number, number]; // w, s, e, n

function tiles([w, s, e, n]: Bbox, step: number): Bbox[] {
  const out: Bbox[] = [];
  for (let x = w; x < e; x += step)
    for (let y = s; y < n; y += step) out.push([x, y, Math.min(x + step, e), Math.min(y + step, n)]);
  return out;
}

// number of tiles a bbox would split into — let callers gate the UI before fetching
export function tileCount(bbox: Bbox, step = TILE_DEG): number {
  const [w, s, e, n] = bbox;
  return Math.ceil((e - w) / step) * Math.ceil((n - s) / step);
}

async function fetchTile(tile: Bbox, token: string, retries = 3): Promise<SignPoint[]> {
  let url: string | null =
    `${API}?fields=${FIELDS}&object_values=${OBJECT_VALUES}` +
    `&bbox=${tile.join(',')}&access_token=${token}`;
  const rows: SignPoint[] = [];
  while (url) {
    let payload: { data?: unknown[]; paging?: { next?: string } } | null = null;
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        const r = await fetch(url);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        payload = await r.json();
        break;
      } catch (e) {
        if (attempt === retries - 1) throw e;
        await new Promise((res) => setTimeout(res, 400 * 2 ** attempt + Math.random() * 300));
      }
    }
    for (const f of payload?.data ?? []) {
      const feat = f as {
        id?: string;
        object_value?: string;
        geometry?: { coordinates?: [number, number] };
        last_seen_at?: string;
      };
      const ov = feat.object_value ?? '';
      const coords = feat.geometry?.coordinates;
      if (!ov.startsWith('regulatory--maximum-speed-limit') || !coords) continue;
      const m = SPEED_RE.exec(ov);
      rows.push({
        lat: coords[1],
        lng: coords[0],
        value: m ? parseInt(m[1], 10) : null,
        sign_id: feat.id ?? '',
        last_seen: feat.last_seen_at ?? null
      });
    }
    url = payload?.paging?.next ?? null;
  }
  return rows;
}

// Fetch all speed-limit signs in a bbox, deduped by sign id across tile edges.
// Throws if the bbox is too large (caller should gate on tileCount first).
export async function fetchSpeedSigns(bbox: Bbox, token: string): Promise<SignPoint[]> {
  const plan = tiles(bbox, TILE_DEG);
  if (plan.length > MAX_TILES) throw new Error(`area too large (${plan.length} tiles) — zoom in`);
  const seen = new Set<string>();
  const out: SignPoint[] = [];
  for (const t of plan) {
    let got: SignPoint[];
    try {
      got = await fetchTile(t, token);
    } catch {
      continue; // flaky API — skip the tile, keep the rest (matches python)
    }
    for (const row of got) {
      if (row.sign_id && seen.has(row.sign_id)) continue;
      seen.add(row.sign_id);
      out.push(row);
    }
  }
  return out;
}
