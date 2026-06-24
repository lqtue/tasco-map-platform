// Full port of OSMData.pm + OSMLanes.pm + OSMDraw.pm + render.pl main loop.
// The HTML emitted uses the same class names as the original style.css /
// <country>.css so those stylesheets can be reused verbatim.

import type {
  Tags,
  Way,
  OsmNode,
  Store,
  Options,
  Lanes,
  RenderResult,
  WayStat,
  RelationMeta,
  Criterion,
  CrossRoad,
  Intersection,
  SheetRow
} from './types';

const LANEHEIGHT = 135;
const STROKEWIDTH = 3;
// JOSM remote control: plain http on 8111, but an https page must use the
// TLS port 8112 or the browser blocks the call as mixed content.
export const JOSM_BASE =
  typeof location !== 'undefined' && location.protocol === 'https:'
    ? 'https://127.0.0.1:8112'
    : 'http://127.0.0.1:8111';
// Overpass endpoints tried in order; mirrors cover rate-limiting / busy dispatchers.
const OVERPASS_ENDPOINTS = [
  'https://overpass-api.de/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
  'https://maps.mail.ru/osm/tools/overpass/api/interpreter'
];

/**
 * POST a query to Overpass, walking the mirror list until one returns JSON.
 * Returns the raw JSON text; throws only if every endpoint fails.
 */
async function fetchOverpass(query: string): Promise<string> {
  let lastErr = '';
  for (const url of OVERPASS_ENDPOINTS) {
    try {
      const res = await fetch(url, { method: 'POST', body: 'data=' + encodeURIComponent(query) });
      const text = await res.text();
      // a JSON payload starts with '{'; anything else is an HTML/text error page
      if (res.ok && text.trimStart().startsWith('{')) return text;
      lastErr = `HTTP ${res.status}`;
    } catch (e) {
      lastErr = (e as Error).message;
    }
  }
  throw new Error(`Overpass unavailable (${lastErr}). All mirrors busy — retry shortly.`);
}

// highway classes treated as "major" crossings (where signage/changes concentrate)
const MAJOR_HW = new Set([
  'motorway', 'motorway_link', 'trunk', 'trunk_link',
  'primary', 'primary_link', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link'
]);

// ---- small helpers -------------------------------------------------------

function escapeEntities(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** number of `|`-separated entries in a lane value (pipes + 1) */
function pipeCount(v: string): number {
  return (v.match(/\|/g) || []).length + 1;
}

/** Perl List::Util max over a list where undef counts as 0; undef only if empty. */
function maxP(arr: (number | undefined)[]): number | undefined {
  if (arr.length === 0) return undefined;
  let m = -Infinity;
  for (const x of arr) {
    const n = x === undefined ? 0 : Number(x);
    const v = Number.isNaN(n) ? 0 : n;
    if (v > m) m = v;
  }
  return m;
}
/** mirrors Perl `defined max(@arr)` : true whenever the array is non-empty */
function definedMax(arr: unknown[]): boolean {
  return arr.length > 0;
}

function rad2deg(r: number): number {
  return (r * 180) / Math.PI;
}

/** Best-effort numeric maxspeed (km/h) from a way's tags; null when unset/non-numeric. */
function parseSpeed(t: Tags): number | null {
  const raw = t['maxspeed'] ?? t['maxspeed:forward'] ?? t['maxspeed:backward'];
  if (!raw) return null;
  const s = raw.trim();
  if (s === 'none' || s === 'signals' || s === 'walk') return null;
  const m = s.match(/(\d+(?:\.\d+)?)/);
  if (!m) return null;
  const n = parseFloat(m[1]);
  return /mph/i.test(s) ? n * 1.609344 : n;
}

export class LaneVisualizer {
  store: Store = { way: [{}], node: [{}], rel: [{}] };
  endnodes: Record<number, number[]>[] = [{}];
  opts: Options;
  LANEWIDTH = 120;
  maxlanes = 4;
  totallength = 0;
  wayCoords: RenderResult['wayCoords'] = {};
  totalStartPoints = 0;
  stats: WayStat[] = [];
  sheetRows: RenderResult['sheetRows'] = [];
  // node id -> crossing roads that share that node (filled by computeIntersections)
  crossByNode: Record<number, CrossRoad[]> = {};
  intersections: Intersection[] = [];

  constructor(opts: Options) {
    this.opts = opts;
  }

  private get waydata() {
    return this.store.way[0];
  }
  /** Days since a way's last OSM edit (null when the data carries no timestamp). */
  private ageDays(id: number): number | null {
    const ts = this.waydata[id]?.timestamp;
    if (!ts) return null;
    return Math.max(0, Math.round((Date.now() - Date.parse(ts)) / 86400000));
  }
  private get nodedata() {
    return this.store.node[0];
  }

  // =========================================================================
  // OSMData.pm
  // =========================================================================

  async readData(query: string, st = 0): Promise<number> {
    let json: string;
    const trimmed = query.trim();
    if (trimmed.startsWith('{')) {
      json = query; // user pasted raw Overpass JSON
    } else {
      json = await fetchOverpass(query);
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let data: any;
    try {
      data = JSON.parse(json);
    } catch {
      // Overpass served an HTML/text error page instead of JSON
      throw new Error('Overpass returned an error (rate-limited or busy). Please retry.');
    }
    if (!data.elements || data.elements.length === 0) return -1;

    this.store.way[st] ||= {};
    this.store.node[st] ||= {};
    this.store.rel[st] ||= {};
    this.endnodes[st] ||= {};

    for (const w of data.elements) {
      if (w.type === 'way' && w.tags && w.tags.highway && w.tags.highway !== 'platform') {
        this.store.way[st][w.id] = { id: w.id, tags: w.tags, nodes: w.nodes, timestamp: w.timestamp };
      } else if (w.type === 'node') {
        this.store.node[st][w.id] = { id: w.id, tags: w.tags || {}, lat: w.lat, lon: w.lon };
      } else if (w.type === 'relation') {
        this.store.rel[st][w.id] = { ...w };
      }
    }

    for (const id in this.store.way[st]) {
      const way = this.store.way[st][id];
      if (!way.tags.highway) continue;
      const first = way.nodes[0];
      const last = way.nodes[way.nodes.length - 1];
      (this.endnodes[st][first] ||= []).push(way.id);
      (this.endnodes[st][last] ||= []).push(way.id);
    }
    return 0;
  }

  organizeWays(): void {
    const ids = Object.keys(this.waydata)
      .map(Number)
      .sort((a, b) => a - b);
    for (const id of ids) {
      const way = this.waydata[id];
      way.begin = way.nodes[0];
      way.end = way.nodes[way.nodes.length - 1];
      for (const x of this.endnodes[0][way.begin] || []) {
        if (x === id) continue;
        const ox = this.waydata[x];
        if (way.begin === ox.nodes[0]) (way.before ||= []).push(x);
        if (way.begin === ox.nodes[ox.nodes.length - 1]) (way.before ||= []).push(x);
      }
      for (const x of this.endnodes[0][way.end] || []) {
        if (x === id) continue;
        const ox = this.waydata[x];
        if (way.end === ox.nodes[0]) (way.after ||= []).push(x);
        if (way.end === ox.nodes[ox.nodes.length - 1]) (way.after ||= []).push(x);
      }
    }
  }

  /** Tags of the first relation in the main store (for the Wikidata length lookup). */
  getRelationMeta(): RelationMeta | null {
    const rels = this.store.rel[0];
    if (!rels) return null;
    const ids = Object.keys(rels);
    if (!ids.length) return null;
    const t: Tags = rels[Number(ids[0])]?.tags || {};
    return {
      name: t['name'] || '',
      ref: t['ref'] || '',
      wikidata: t['wikidata'] || ''
    };
  }

  /** Overpass query for all highways sharing a node with our road (the crossing roads). */
  buildCrossingQuery(): string {
    const ids = Object.keys(this.waydata).join(',');
    // `>;out skel` also returns the crossing ways' node coords so we can compute turn side
    return `[out:json][timeout:60];way(id:${ids})->.road;node(w.road)->.rn;way(bn.rn)[highway]->.cross;(.cross; - .road;);out body qt;>;out skel qt;`;
  }

  /** node coordinates from the main store, falling back to the crossing store (slot 2). */
  private nodeCoord(id: number): OsmNode | undefined {
    return this.nodedata[id] || this.store.node[2]?.[id];
  }

  /** compass bearing (0–360°, 0 = north, clockwise) from one node to another. */
  private compass(from: OsmNode, to: OsmNode): number {
    const latR = ((from.lat + to.lat) / 2) * (Math.PI / 180);
    const dE = (to.lon - from.lon) * Math.cos(latR);
    const dN = to.lat - from.lat;
    return ((Math.atan2(dE, dN) * 180) / Math.PI + 360) % 360;
  }

  /** which way a crossing road branches off, relative to our heading through node n. */
  private crossingDir(road: CrossRoad, n: number, ourHeading: number): 'left' | 'right' | 'through' {
    const c = this.store.way[2]?.[road.id];
    if (!c) return 'through';
    const j = c.nodes.indexOf(n);
    if (j < 0) return 'through';
    const branchId = c.nodes[j + 1] ?? c.nodes[j - 1];
    const here = this.nodeCoord(n);
    const branch = this.nodeCoord(branchId);
    if (!here || !branch) return 'through';
    const turn = this.normalizeAngle(this.compass(here, branch) - ourHeading);
    if (Math.abs(turn) <= 25 || Math.abs(turn) >= 160) return 'through';
    return turn > 0 ? 'right' : 'left';
  }

  /**
   * Match crossing ways (loaded into store slot 2 by buildCrossingQuery) against our
   * road's nodes. A shared node = an intersection. Fills crossByNode + intersections.
   */
  computeIntersections(): void {
    this.crossByNode = {};
    this.intersections = [];
    const cross = this.store.way[2];
    if (!cross) return;

    const ourWayIds = new Set(Object.keys(this.waydata).map(Number));
    const ourNodes = new Set<number>();
    for (const id of ourWayIds) for (const n of this.waydata[id].nodes) ourNodes.add(n);

    // refs that belong to our own road (so a continuation isn't counted as a crossing)
    const ourRefs = new Set<string>();
    const rel = this.getRelationMeta();
    if (rel?.ref) ourRefs.add(rel.ref);
    for (const id of ourWayIds) {
      const rf = this.waydata[id].tags['ref'];
      if (rf) ourRefs.add(rf);
    }

    // non-vehicular / placeholder highways we don't treat as road intersections
    const SKIP = new Set([
      'footway', 'path', 'steps', 'pedestrian', 'cycleway', 'bridleway',
      'corridor', 'platform', 'construction', 'proposed', 'raceway'
    ]);

    for (const cidStr of Object.keys(cross)) {
      const cid = Number(cidStr);
      if (ourWayIds.has(cid)) continue;
      const c = cross[cid];
      const hw = c.tags['highway'];
      if (!hw || SKIP.has(hw)) continue;
      if (c.tags['ref'] && ourRefs.has(c.tags['ref'])) continue; // same road, other piece
      for (const n of c.nodes) {
        if (!ourNodes.has(n)) continue;
        (this.crossByNode[n] ||= []).push({
          id: cid,
          name: c.tags['name'] || '',
          ref: c.tags['ref'] || '',
          highway: hw
        });
      }
    }

    for (const nStr of Object.keys(this.crossByNode)) {
      const n = Number(nStr);
      const seen = new Set<number>();
      this.crossByNode[n] = this.crossByNode[n].filter((r) => !seen.has(r.id) && seen.add(r.id));
      const nd = this.nodedata[n];
      this.intersections.push({ nodeId: n, lat: nd?.lat, lon: nd?.lon, roads: this.crossByNode[n] });
    }
  }

  private listtags(obj: Way | OsmNode): string {
    const t = obj.tags;
    let ret = '';
    for (const k of Object.keys(t).sort()) ret += k + ' = ' + t[k] + '\n';
    return escapeEntities(ret);
  }

  private calcDistance(a: number, b: number): number {
    const na = this.nodedata[a];
    const nb = this.nodedata[b];
    const lat = ((na.lat + nb.lat) / 2) * 0.01745;
    const dx = 111.3 * Math.cos(lat) * (na.lon - nb.lon);
    const dy = 111.3 * (na.lat - nb.lat);
    return Math.sqrt(dx * dx + dy * dy) * 1000;
  }

  /** direction of x->a, both are node objects */
  private calcDirection(x: OsmNode, a: OsmNode): number {
    const lat = x.lat * 0.01745;
    const dxa = 111.3 * Math.cos(lat) * (a.lon - x.lon);
    const dya = 111.3 * (a.lat - x.lat);
    if (dxa === 0) return 0;
    let ang = rad2deg(Math.atan(Math.abs(dya) / Math.abs(dxa)));
    if (dxa >= 0 && dya >= 0) ang = -ang;
    else if (dxa < 0 && dya >= 0) ang = -180 + ang;
    else if (dxa < 0 && dya < 0) ang = 180 - ang;
    else ang = 0 + ang;
    return ang;
  }

  private calcLength(w: number): number {
    const way = this.waydata[w];
    if (!way || !way.nodes) return 0;
    let l = 0;
    for (let i = 1; i < way.nodes.length; i++) {
      l += this.calcDistance(way.nodes[i - 1], way.nodes[i]);
    }
    return l;
  }

  private normalizeAngle(a: number): number {
    while (a < -180) a += 360;
    while (a > 180) a -= 360;
    return a;
  }

  // equirectangular metres between two [lat,lon] points (same approx as calcDistance)
  private distLL(a: [number, number], b: [number, number]): number {
    const lat = ((a[0] + b[0]) / 2) * 0.01745;
    const dx = 111.3 * Math.cos(lat) * (a[1] - b[1]);
    const dy = 111.3 * (a[0] - b[0]);
    return Math.sqrt(dx * dx + dy * dy) * 1000;
  }

  // compass bearing 0–360 (0=N, cw) from first to last point of a line
  private lineBearing(line: [number, number][]): number {
    const a = line[0];
    const b = line[line.length - 1];
    const latR = ((a[0] + b[0]) / 2) * 0.01745;
    const dE = (b[1] - a[1]) * Math.cos(latR);
    const dN = b[0] - a[0];
    return ((Math.atan2(dE, dN) * 180) / Math.PI + 360) % 360;
  }

  /** Pair opposing carriageways of a divided road: for each oneway way, find the
   *  oneway way running ~anti-parallel and laterally close. Fills wayCoords[id].pairId.
   *  ponytail: midpoint-to-nearest-vertex distance, O(n²); fine for one route. */
  private pairCarriageways(): void {
    const MAX_LATERAL = 60; // metres between the two carriageways
    const ids = Object.keys(this.wayCoords).map(Number);
    const info = ids
      .map((id) => {
        const line = this.wayCoords[id].line;
        const t = this.waydata[id]?.tags || {};
        return {
          id,
          line,
          oneway: t['oneway'] !== undefined && t['oneway'] !== 'no',
          bearing: this.lineBearing(line),
          mid: line[Math.floor(line.length / 2)]
        };
      })
      .filter((w) => w.oneway && w.line.length > 1);
    for (const a of info) {
      let bestId: number | undefined;
      let bestDist = MAX_LATERAL;
      for (const b of info) {
        if (b.id === a.id) continue;
        let dh = Math.abs(a.bearing - b.bearing) % 360;
        if (dh > 180) dh = 360 - dh;
        if (Math.abs(dh - 180) > 35) continue; // must run opposite (~180°)
        let d = Infinity;
        for (const p of b.line) d = Math.min(d, this.distLL(a.mid, p));
        if (d < bestDist) {
          bestDist = d;
          bestId = b.id;
        }
      }
      if (bestId !== undefined) this.wayCoords[a.id].pairId = bestId;
    }
  }

  // =========================================================================
  // OSMLanes.pm
  // =========================================================================

  private getLanes(obj: Way): void {
    const t = obj.tags;
    const lanedir: string[] = [];
    const st: { f: (number | undefined)[]; b: (number | undefined)[]; m: (number | undefined)[]; l: (number | undefined)[] } = {
      f: [],
      b: [],
      m: [],
      l: []
    };

    for (const k of Object.keys(t)) {
      if (/:lanes/.test(k)) {
        const c = pipeCount(t[k]);
        if (/:forward/.test(k)) st.f.push(c);
        else if (/:backward/.test(k)) st.b.push(c);
        else if (/:both_ways/.test(k)) st.m.push(c);
        else st.l.push(c);
      }
    }

    const num = (v: string | undefined) => (v === undefined ? undefined : Number(v));
    st.f.push(num(t['lanes:forward']));
    st.b.push(num(t['lanes:backward']));
    st.m.push(num(t['lanes:both_ways']));
    st.l.push(num(t['lanes']));

    if (t['lanes:forward'] !== undefined && t['lanes'] !== undefined && t['lanes:backward'] === undefined) {
      st.b.push(Number(t['lanes']) - Number(t['lanes:forward']));
    }
    if (t['lanes:backward'] !== undefined && t['lanes'] !== undefined && t['lanes:forward'] === undefined) {
      st.f.push(Number(t['lanes']) - Number(t['lanes:backward']));
    }
    // (the two original `!defined defined max(...)` blocks are dead code in
    //  the Perl source and never run, so they are intentionally omitted.)

    const oneway = t['oneway'] !== undefined && t['oneway'] !== 'no';
    if (oneway) {
      st.f.push(num(t['lanes']));
    } else {
      if (!definedMax(st.f)) st.f.push(t['lanes'] !== undefined ? Number(t['lanes']) / 2 : undefined);
      if (!definedMax(st.b)) st.b.push(t['lanes'] !== undefined ? Number(t['lanes']) / 2 : undefined);
    }

    if (oneway) {
      st.f.push(1);
      st.f.push(...st.l);
    } else {
      st.f.push(1);
      st.b.push(1);
    }

    const fwdlane = maxP(st.f) || 0;
    const bcklane = maxP(st.b) || 0;
    const bothlane = maxP(st.m) || 0;

    let nolane = 0;
    if (t['traffic_calming'] === 'island') nolane = 1;
    if (t['lanes'] !== undefined && Number(t['lanes']) > fwdlane + bcklane + bothlane) {
      nolane = Number(t['lanes']) - fwdlane - bcklane - bothlane;
    }

    if (!obj.reversed) {
      for (let i = 0; i < bcklane; i++) lanedir.push('backward');
      for (let i = 0; i < bothlane; i++) lanedir.push('bothlane');
      for (let i = 0; i < nolane; i++) lanedir.push('nolane');
      for (let i = 0; i < fwdlane; i++) lanedir.push('forward');
    } else {
      for (let i = 0; i < fwdlane; i++) lanedir.push('backward');
      for (let i = 0; i < bothlane; i++) lanedir.push('bothlane');
      for (let i = 0; i < nolane; i++) lanedir.push('nolane');
      for (let i = 0; i < bcklane; i++) lanedir.push('forward');
    }

    obj.lanes = {
      fwd: fwdlane,
      bck: bcklane,
      both: bothlane,
      none: nolane,
      list: lanedir,
      numlanes: lanedir.length
    } as Lanes;
  }

  /** generic reader for *:lanes tagging -> array, one entry per lane */
  private getLaneTags(obj: Way, tag: string, options = ''): string[] {
    const t = obj.tags;
    const lanes = obj.lanes!;
    const out: string[] = [];
    for (let i = 0; i < lanes.numlanes; i++) out.push('');

    if (t[tag] !== undefined && !/nonolanes/.test(options)) {
      for (let i = 0; i < lanes.numlanes; i++) out[i] = t[tag];
    }
    if (t[tag + ':backward'] !== undefined) {
      for (let i = 0; i < lanes.bck; i++) out[i] = t[tag + ':backward'];
    }
    if (t[tag + ':both_ways'] !== undefined) {
      for (let i = 0; i < lanes.both; i++) out[i + lanes.bck] = t[tag + ':both_ways'];
    }
    if (t[tag + ':forward'] !== undefined) {
      for (let i = 0; i < lanes.fwd; i++) out[i + lanes.bck + lanes.both + lanes.none] = t[tag + ':forward'];
    }
    if (t[tag + ':lanes'] !== undefined) {
      const tmp = t[tag + ':lanes'].split('|');
      for (let i = 0; i < tmp.length; i++) {
        if (tmp[i] !== undefined && tmp[i] !== '' && !/^\s*$/.test(tmp[i])) out[i] = tmp[i];
      }
    }
    if (t[tag + ':lanes:backward'] !== undefined) {
      const tmp = t[tag + ':lanes:backward'].split('|');
      for (let i = 0; i < tmp.length; i++) {
        if (tmp[i] !== undefined && tmp[i] !== '' && !/^\s*$/.test(tmp[i])) out[lanes.bck - 1 - i] = tmp[i];
      }
    }
    if (t[tag + ':lanes:both_ways'] !== undefined) {
      const tmp = t[tag + ':lanes:both_ways'].split('|');
      for (let i = 0; i < tmp.length; i++) {
        if (tmp[i] !== undefined && tmp[i] !== '' && !/^\s*$/.test(tmp[i])) out[lanes.bck + i] = tmp[i];
      }
    }
    if (t[tag + ':lanes:forward'] !== undefined) {
      const tmp = t[tag + ':lanes:forward'].split('|');
      for (let i = 0; i < tmp.length; i++) {
        if (tmp[i] !== undefined && tmp[i] !== '' && !/^\s*$/.test(tmp[i]))
          out[lanes.bck + lanes.both + lanes.none + i] = tmp[i];
      }
    }

    if (!/noreverse/.test(options) && obj.reversed) out.reverse();
    return out;
  }

  private getWidth(obj: Way): void {
    const lanes = obj.lanes!;
    const raw = this.getLaneTags(obj, 'width', 'nonolanes');
    const width: number[] = raw.map((s) => (s ? parseFloat(s) || 0 : 0));

    if (lanes.none) {
      let pos = lanes.bck + lanes.both;
      if (obj.reversed) pos = lanes.fwd + lanes.both;
      width[pos] = 4 * 0.6;
      if (obj.tags['traffic_calming:width'] !== undefined) width[pos] = parseFloat(obj.tags['traffic_calming:width']) || 0;
    }

    if (obj.tags['width'] !== undefined) {
      lanes.haswidth = 1;
      const lw = (parseFloat(obj.tags['width']) || 0) / lanes.numlanes;
      for (let i = 0; i < lanes.numlanes; i++) if (!width[i]) width[i] = lw;
    }
    lanes.totalwidth = 0;
    for (let i = 0; i < lanes.numlanes; i++) {
      if (width[i]) {
        lanes.haswidth = 1;
        lanes.totalwidth += width[i];
      } else {
        lanes.totalwidth += 4;
      }
    }
    lanes.width = width;
  }

  private getChange(obj: Way): void {
    const lanes = obj.lanes!;
    const change = this.getLaneTags(obj, 'change', 'noreverse');
    for (let c = 0; c < change.length; c++) {
      change[c] = change[c].replace(/yes/, '').replace(/only_left/, 'not_right').replace(/only_right/, 'not_left');
    }
    if (obj.tags['overtaking'] === 'no') {
      if (lanes.bck !== 0) change[lanes.bck - 1] += ' not_left';
      if (lanes.fwd !== 0) change[lanes.bck + lanes.both] += ' not_left';
    }
    change[0] += lanes.bck ? ' not_right' : ' not_left';
    change[change.length - 1] += lanes.fwd ? ' not_right' : ' not_left';

    if (obj.reversed) change.reverse();
    lanes.change = change;
  }

  private placementCountLanes(obj: Way, pmAll?: string, pmFwd?: string, pmBck?: string): number {
    const pm = pmAll || pmFwd || pmBck;
    const lanes = obj.lanes!;
    let offset: number;
    let p: (string | number)[] = [];
    let d: number | undefined;

    if (pm !== undefined) {
      p = pm.split(':');
      if (p[0] === 'right_of') p[1] = Number(p[1]) + 1;
      if (p[0] === 'middle_of') p[1] = Number(p[1]) + 0.5;
      if (p[0] === 'transition') p[1] = undefined as unknown as number;

      if (pmFwd !== undefined) d = lanes.bck + (Number(p[1]) - 1);
      else if (pmBck !== undefined) d = lanes.bck - (Number(p[1]) - 1);
      else d = Number(p[1]) - 1;
    }

    if (d !== undefined && p[1] !== undefined && !Number.isNaN(d)) {
      if (obj.reversed === 0 || obj.reversed === undefined) offset = this.maxlanes - d;
      else offset = this.maxlanes - lanes.list.length + d;
    } else {
      offset = this.maxlanes - (lanes.fwd + lanes.bck + lanes.both) / 2;
    }
    return offset;
  }

  private placementStartEnd(obj: Way): number {
    const t = obj.tags;
    const lanes = obj.lanes!;
    let offset: number;
    let offend: number;
    if (obj.reversed === 0 || obj.reversed === undefined) {
      offset = this.placementCountLanes(
        obj,
        t['placement:end'] || t['placement'],
        t['placement:forward:end'] || t['placement:forward'],
        t['placement:backward:end'] || t['placement:backward']
      );
      offend = this.placementCountLanes(
        obj,
        t['placement:start'] || t['placement'],
        t['placement:forward:start'] || t['placement:forward'],
        t['placement:backward:start'] || t['placement:backward']
      );
    } else {
      offset = this.placementCountLanes(
        obj,
        t['placement:start'] || t['placement'],
        t['placement:forward:start'] || t['placement:forward'],
        t['placement:backward:start'] || t['placement:backward']
      );
      offend = this.placementCountLanes(
        obj,
        t['placement:end'] || t['placement'],
        t['placement:forward:end'] || t['placement:forward'],
        t['placement:backward:end'] || t['placement:backward']
      );
    }
    lanes.offend = offend;
    lanes.offset = (offset + offend) / 2;
    let tilt = offset - offend;
    tilt = rad2deg(Math.atan2(tilt * this.LANEWIDTH, LANEHEIGHT));
    lanes.tilt = -tilt;
    return lanes.offset;
  }

  private getPlacement(obj: Way): void {
    const t = obj.tags;
    const lanes = obj.lanes!;
    let offset: number;

    if (this.opts.lanewidth && lanes.haswidth) {
      offset = 0;
      if (t['placement'] !== undefined) {
        if (t['oneway'] === 'yes') {
          const p = t['placement'].split(':');
          for (let i = 0; i < Number(p[1]); i++) {
            if (i === Number(p[1]) - 1) {
              if (p[0] === 'right_of') offset += lanes.width![i] - 12 / this.LANEWIDTH;
              if (p[0] === 'middle_of') offset += lanes.width![i] / 2 - 12 / this.LANEWIDTH;
            } else {
              offset += lanes.width![i] - 12 / this.LANEWIDTH;
            }
          }
        }
      } else {
        offset = lanes.totalwidth! / 2;
      }
      offset = this.maxlanes * 4 - offset;
      offset *= this.LANEWIDTH / 4;
    } else if (this.opts.usePlacement) {
      if (t['placement:start'] !== undefined || t['placement:end'] !== undefined) {
        offset = this.placementStartEnd(obj);
      } else {
        offset = this.placementCountLanes(obj, t['placement'], t['placement:forward'], t['placement:backward']);
      }
      offset *= this.LANEWIDTH;
    } else {
      offset = this.maxlanes - lanes.bck - lanes.both / 2;
      if (obj.reversed) offset = this.maxlanes - lanes.fwd - lanes.both / 2;
      offset *= this.LANEWIDTH;
    }
    lanes.offset = offset;
  }

  private makeAccessColors(obj: Way): void {
    const l = obj.lanes!;
    for (let i = 0; i < l.numlanes; i++) {
      const eq = (arr: string[] | undefined, v: string) => (arr?.[i] || '') === v;
      if (
        eq(l.bicycle, 'designated') ||
        eq(l.bicycle, 'official') ||
        eq(l.foot, 'designated') ||
        eq(l.foot, 'official') ||
        eq(l.psv, 'designated') ||
        eq(l.bus, 'designated') ||
        eq(l.access, 'no') ||
        eq(l.vehicle, 'no')
      ) {
        l.access![i] = (l.access![i] || '') + ' restrictlane';
      }
    }
  }

  private inspectLanes(obj: Way): void {
    this.getLanes(obj);
    this.getWidth(obj);
    this.getPlacement(obj);
    this.getChange(obj);

    const l = obj.lanes!;
    l.turn = this.getLaneTags(obj, 'turn');
    l.maxspeed = this.getLaneTags(obj, 'maxspeed', 'nonolanes');
    l.minspeed = this.getLaneTags(obj, 'minspeed', 'nonolanes');
    l.bicycle = this.getLaneTags(obj, 'bicycle', 'nonolanes');
    l.bus = this.getLaneTags(obj, 'bus');
    l.psv = this.getLaneTags(obj, 'psv');
    l.foot = this.getLaneTags(obj, 'foot', 'nonolanes');
    l.access = this.getLaneTags(obj, 'access');
    l.vehicle = this.getLaneTags(obj, 'vehicle');
    l.hgv = this.getLaneTags(obj, 'hgv', 'nonolanes');
    this.makeAccessColors(obj);

    const keys = [
      'destination',
      'destination:ref',
      'destination:colour',
      'destination:symbol',
      'destination:country',
      'destination:arrow',
      'destination:int_ref',
      'destination:to',
      'destination:ref:to',
      'destination:colour:to',
      'destination:symbol:to',
      'destination:arrow:to',
      'destination:int_ref:to',
      'destination:distance'
    ];
    for (const k of keys) {
      const sk = k.replace(/[:_]/g, '');
      (l as Record<string, unknown>)[sk] = this.getLaneTags(obj, k);
    }
  }

  // =========================================================================
  // OSMDraw.pm
  // =========================================================================

  private makeMaxspeed(id: number, item: string): string {
    const name = item.substring(0, 3);
    const t = this.waydata[id].tags;
    let out = '';
    let maxforward = t[item + ':forward'] || t[item] || 'unkwn';
    let maxbackward = t[item + ':backward'] || t[item] || 'unkwn';
    const fwdclass = maxforward;
    const bckclass = maxbackward;
    maxforward = maxforward.replace(/none/, '');
    maxbackward = maxbackward.replace(/none/, '');

    if (maxforward === maxbackward) {
      out = `<div class="${name} ${fwdclass}">${maxforward}</div>`;
    } else if (this.waydata[id].reversed) {
      out = `<div class="${name} fwd ${fwdclass}">${maxforward}</div>`;
      out += `<div class="${name} bck ${bckclass}">${maxbackward}</div>`;
    } else {
      out = `<div class="${name} bck ${bckclass}">${maxbackward}</div>`;
      out += `<div class="${name} fwd ${fwdclass}">${maxforward}</div>`;
    }

    for (const mc of [':hgv', ':hgv:forward', ':hgv:backward']) {
      if (t[item + mc]) {
        out += '<div class="maxcont">';
        out += `<div class="${name} ">${t[item + mc]}</div>`;
        out += '<div class="condition hgv">&nbsp;</div>';
        out += '</div>';
      }
    }
    for (const mc of [':conditional', ':forward:conditional', ':backward:conditional']) {
      if (t[item + mc]) {
        const str = t[item + mc];
        const re = /([^(;]+)\s*@\s*(\(([^)]+)\)|([^;]+))/g;
        let m: RegExpExecArray | null;
        while ((m = re.exec(str)) !== null) {
          const what = m[1];
          let when = (m[3] || '') + (m[4] || '');
          const title = m[1] + ' @ ' + (m[3] || '') + (m[4] || '');
          let cls = '';
          when = when.replace(/:00/g, '');
          if (when === 'wet') {
            when = '';
            cls = 'wet';
          }
          out += `<div class="maxcont" title="${title}">`;
          out += `<div class="${name} ">${what}</div>`;
          out += `<div class="condition ${cls}">${when}</div>`;
          out += '</div>';
        }
      }
    }
    return out;
  }

  private makeSigns(obj: Way, i?: number): string {
    let t: Tags;
    let out = '';
    if (i !== undefined) {
      const l = obj.lanes!;
      t = {
        access: l.access?.[i] || '',
        bicycle: l.bicycle?.[i] || '',
        foot: l.foot?.[i] || '',
        bus: l.bus?.[i] || '',
        psv: l.psv?.[i] || '',
        hgv: l.hgv?.[i] || ''
      };
    } else {
      t = obj.tags;
    }
    const v = (k: string) => t[k] || '';
    if (v('overtaking') === 'no' || v('overtaking:forward') === 'no' || v('overtaking:backward') === 'no')
      out += '<div class="overtaking">&nbsp;</div>';
    if (v('overtaking:hgv') === 'no' || v('overtaking:hgv:backward') === 'no' || v('overtaking:hgv:forward') === 'no')
      out += '<div class="overtakinghgv">&nbsp;</div>';
    if (v('bicycle') === 'no') out += '<div class="bicycleno">&nbsp;</div>';
    if (v('bicycle') === 'designated' || v('bicycle') === 'official') out += '<div class="bicycledesig">&nbsp;</div>';
    if (v('foot') === 'no') out += '<div class="footno">&nbsp;</div>';
    if (v('foot') === 'designated' || v('foot') === 'official') out += '<div class="footdesig">&nbsp;</div>';
    if (v('psv') === 'designated' || v('psv') === 'official') {
      out += '<div class="busdesig">&nbsp;</div>';
      out += '<div class="taxiyes">&nbsp;</div>';
    }
    if (v('bus') === 'designated' || v('bus') === 'official') out += '<div class="busdesig">&nbsp;</div>';
    if (v('hgv') === 'no') out += '<div class="hgvno">&nbsp;</div>';
    if (v('hgv') === 'designated' || v('hgv') === 'official') out += '<div class="hgvdesig">&nbsp;</div>';
    if (v('motorroad') === 'yes') out += '<div class="motorroad">&nbsp;</div>';
    if (v('junction') === 'roundabout') out += '<div class="roundabout">&nbsp;</div>';
    return out;
  }

  private makeNodeSigns(id: number): string {
    const st: Record<string, number> = {};
    const way = this.waydata[id];
    for (const n of way.nodes) {
      if (n === way.begin) continue;
      const nt = this.nodedata[n]?.tags || {};
      if (nt.highway === 'traffic_signals') st['traffic_signals'] = 1;
      if (nt.highway === 'give_way') st['give_way'] = 1;
      if (nt.highway === 'crossing') st['crossing'] = 1;
      if (nt.highway === 'stop') st['stop'] = 1;
      if (nt.highway === 'mini_roundabout') st['roundabout'] = 1;
    }
    let out = '';
    for (const s of Object.keys(st)) out += `<div class="${s}">&nbsp;</div>`;
    return out;
  }

  /** classify a single ref string into a shield letter-class, per country */
  private refClass(r: string): string {
    const c = this.opts.country;
    if (c === 'de') {
      if (/^\s*A/.test(r)) return 'A';
      if (/^\s*B/.test(r)) return 'B';
      if (/^\s*E/.test(r)) return 'E';
      if (/^\s*S/.test(r)) return 'S';
    } else if (c === 'be') {
      if (/^\s*A/.test(r)) return 'A';
      if (/^\s*N/.test(r)) return 'N';
      if (/^\s*E/.test(r)) return 'E';
      if (/^\s*R/.test(r)) return 'R';
    } else if (c === 'vn') {
      if (/^\s*CT/.test(r)) return 'A'; // expressway (cao tốc)
      if (/^\s*QL/.test(r)) return 'B'; // national highway (quốc lộ)
      if (/^\s*(AH|E)/.test(r)) return 'E'; // Asian Highway
      if (/^\s*(DT|ĐT|TL)/.test(r)) return 'K'; // provincial (đường tỉnh)
    }
    return '';
  }

  private printRef(r: string): string {
    const cr = this.refClass(r);
    if (/^\s*$/.test(r)) return '';
    return `<span class="ref${cr}">${r}</span>`;
  }

  private makeRef(ref: string): string {
    let o = '';
    if (!ref) return o;
    let cr = this.opts.country === 'be' ? 'N' : this.opts.country === 'vn' ? 'S' : 'K';
    for (const r of ref.split(';')) {
      const c = this.refClass(r);
      if (c) cr = c;
      if (r !== '') o += `<div class="ref${cr}">${r}</div>`;
    }
    return o;
  }

  private destArrow(dir: string): string {
    if (dir === 'left') return "<span class='l'>&#x2794;</span> ";
    if (dir === 'slight_left') return "<span class='sl'>&#x2794;</span> ";
    if (dir === 'through') return "<span class='t'>&#x2794;</span> ";
    return '';
  }

  private makeDestination(lane: number, way: Tags, lanes: Lanes): string {
    let o = '';
    let cr = 'K';
    const a = (key: string) => ((lanes as Record<string, unknown>)[key] as string[] | undefined)?.[lane] ?? '';
    let dest = a('destination');
    const roadref = way['ref'] || '';
    let ref = a('destinationref');
    const refto = a('destinationrefto');
    const irefto = a('destinationintrefto');
    const to = a('destinationto');
    const symbolto = a('destinationsymbolto');
    const destcol = a('destinationcolour');
    const destcolto = a('destinationcolourto');
    let destsym = a('destinationsymbol');
    const destcountry = a('destinationcountry');
    let arrow = a('destinationarrow');
    const arrowto = a('destinationarrowto');
    const distance = a('destinationdistance');
    const turnLane = lanes.turn?.[lane] || '';

    ref = ref.replace(/;/g, ' / ');
    destsym = destsym.replace(/none/g, '');
    arrow = arrow.replace(/none/g, '');

    if (!(ref || dest || destsym || destcountry || refto || to)) return o;

    o += '<div class="refcont">';
    if (this.opts.country === 'be') cr = 'N';
    else if (this.opts.country === 'vn') cr = 'S';
    else cr = 'K';
    if (/^\s*B/.test(roadref)) cr = 'B';
    if (/^\s*A/.test(roadref) || /^\s*A/.test(ref)) cr = 'A';
    if (this.opts.country === 'vn') {
      if (/QL/.test(roadref) || /QL/.test(ref)) cr = 'B';
      if (/CT/.test(roadref) || /CT/.test(ref)) cr = 'A';
    }

    o += `<div class="${cr}" >`;

    const dests = dest.split(';');
    let reftos = refto.split(';');
    let ireftos = irefto.split(';');
    let tos = to.split(';');
    let symboltos = symbolto.split(';');
    let cols = destcol.split(';');
    let coltos = destcolto.split(';');
    let syms = destsym.split(';');
    const ctr = destcountry.split(';');
    let arro = arrow.split(';');
    let arroto = arrowto.split(';');
    let distances = distance.split(';');

    const fill = (arr: string[], n: number) => (arr.length === 1 ? new Array(n).fill(arr[0]) : arr);

    let entries = Math.max(ireftos.length, reftos.length, tos.length);
    if (entries > 1) {
      ireftos = fill(ireftos, entries);
      reftos = fill(reftos, entries);
      tos = fill(tos, entries);
      coltos = fill(coltos, entries);
      symboltos = fill(symboltos, entries);
      arroto = fill(arroto, entries);
    }

    for (let i = 0; i < entries; i++) {
      let colStyle = '';
      if (coltos[i]) {
        let tc = '';
        let cv = coltos[i];
        if (cv === 'white' || /ffffff/.test(cv)) tc = 'color:black;';
        if (cv === 'blue') {
          tc = 'color:white';
          cv = '#5078D0';
        }
        colStyle = `style="background-color:${cv};${tc}"`;
      }
      let symClass = symboltos[i] || '';
      if (symClass) symClass += !reftos[i] && !ireftos[i] && !tos[i] ? ' symbolonly' : ' symbol';
      symClass = 'dest refto ' + symClass;
      o += `<div class="${symClass}">`;
      o += `<span ${colStyle}>`;
      if (arroto[i] && arroto[i] !== turnLane) {
        o += this.destArrow(arroto[i]);
        if (arroto[i] === 'slight_right') tos[i] = (tos[i] || '') + " <span class='sr'>&#x2794;</span>";
        if (arroto[i] === 'right') tos[i] = (tos[i] || '') + " <span class='r'>&#x2794;</span>";
      }
      o += this.printRef((reftos[i] || '') + (ireftos[i] || ''));
      o += (tos[i] || '&nbsp;') + '</span>';
      o += '</div>';
    }

    entries = Math.max(dests.length, syms.length);
    if (entries > 1) {
      cols = fill(cols, entries);
      syms = fill(syms, entries);
      arro = fill(arro, entries);
      distances = fill(distances, entries);
    }

    for (let i = 0; i < entries; i++) {
      let colStyle = '';
      if (cols[i]) {
        let tc = '';
        let cv = cols[i];
        if (cv === 'white' || /ffffff/.test(cv)) tc = 'color:black;';
        if (cv === 'blue') {
          tc = 'color:white';
          cv = '#5078D0';
        }
        colStyle = `style="background-color:${cv};${tc}"`;
      }
      let symClass = syms[i] || '';
      if (symClass) symClass += !dests[i] ? ' symbolonly' : ' symbol';
      symClass = 'dest ' + symClass;
      o += `<div class="${symClass}">`;
      o += `<span ${colStyle}>`;
      let dtext = dests[i] || '';
      if (distances[i]) {
        dtext += '  ' + distances[i];
        if (!/(mi|nmi|km|m|")/.test(distances[i])) dtext += ' km';
      }
      if (arro[i] && arro[i] !== turnLane) {
        o += this.destArrow(arro[i]);
        if (arro[i] === 'slight_right') dtext += " <span class='sr'>&#x2794;</span>";
        if (arro[i] === 'right') dtext += " <span class='r'>&#x2794;</span>";
      }
      o += dtext || '&nbsp;';
      if (ctr.length === dests.length && ctr[i] !== 'none' && ctr[i]) o += `<span class="destCountry">${ctr[i]}</span>`;
      o += '</span>';
      o += '</div>';
    }

    o += '<div class="clear">&nbsp;</div>';

    if (ctr.length !== dests.length) {
      for (const c of ctr) {
        if (c === 'none') continue;
        o += `<div class="destCountry">${c}</div>`;
      }
    }

    if (ref) {
      const refs = ref.split('/');
      for (const r of refs.reverse()) o += this.printRef(r);
    }

    o += '</div></div>';
    return o;
  }

  private makeAllDestinations(id: number, st: number, correspondingid?: number): string[] {
    const t = this.store.way[st][id].tags;
    const lanes = this.store.way[st][id].lanes!;
    const tilt = -(this.store.way[st][correspondingid ?? id].lanes?.tilt || 0);
    const destinations: string[] = [];
    for (let i = 0; i < lanes.numlanes; i++) destinations.push(this.makeDestination(i, t, lanes));
    for (let i = 0; i < lanes.numlanes; i++) {
      if (destinations[i]) {
        let w = '';
        if (destinations[i] === destinations[i + 1]) {
          w = 'double';
          destinations[i + 1] = '';
          if (destinations[i] === destinations[i + 2]) {
            w = 'triple';
            destinations[i + 2] = '';
            if (destinations[i] === destinations[i + 3]) {
              w = 'quadruple';
              destinations[i + 3] = '';
            }
          }
        }
        destinations[i] = `<div class="destination ${w}" style="transform:skewX(${tilt}deg)">${destinations[i]}</div>`;
      }
    }
    return destinations;
  }

  private getBestNext(id: number): number | undefined {
    const way = this.waydata[id];
    let angle = 0;
    let ra = 0;
    let minangle = 180;
    let realnext: number | undefined;
    const n = way.nodes;
    const fromdirection = this.calcDirection(this.nodedata[n[n.length - 1]], this.nodedata[n[n.length - 2]]);
    if (way.tags['junction'] === 'roundabout') {
      ra = 1;
      minangle = 0;
    }
    if (!way.after) return undefined;
    for (const nx of way.after) {
      const nxw = this.waydata[nx];
      if (nxw.nodes[0] === n[n.length - 1]) {
        angle = this.calcDirection(this.nodedata[nxw.nodes[1]], this.nodedata[nxw.nodes[0]]);
      } else {
        angle = this.calcDirection(this.nodedata[nxw.nodes[nxw.nodes.length - 2]], this.nodedata[nxw.nodes[nxw.nodes.length - 1]]);
      }
      angle = this.normalizeAngle(fromdirection - angle);
      angle = Math.abs(angle);
      if ((ra === 0 && angle < minangle) || (ra === 1 && angle > minangle)) {
        minangle = angle;
        realnext = nx;
      }
    }
    return realnext;
  }

  private makeTurns(turns: string, dir: string): string {
    const t = ';' + turns;
    let o = `<div class="turns ${dir}">`;
    if (/reverse/.test(t)) o += '&#x21b6;';
    if (/merge_to_left/.test(t)) o += '<div style="display:inline-block;transform: rotate(45deg)">&#x293A;</div>';
    if (/sharp_left/.test(t)) o += '&#x2198;';
    if (/;left/.test(t)) o += '&#x21B0;';
    if (/slight_left/.test(t)) o += '&#x2196;';
    if (/through/.test(t)) o += '&#x2191;';
    if (/slight_right/.test(t)) o += '&#x2197;';
    if (/;right/.test(t)) o += '&#x21B1;';
    if (/sharp_right/.test(t)) o += '&#x2199;';
    if (/merge_to_right/.test(t)) o += '<div style="display:inline-block;transform: rotate(225deg)">&#x2938;</div>';
    o += '</div>';
    return o;
  }

  private makeWaylayout(id: number, next?: number): string {
    const way = this.waydata[id];
    let out = '<div class="waylayout">';
    let cntways = 0;
    let connectsangle = -400;
    let connectsid = 0;
    const stangle = 0;
    for (const i of this.endnodes[1][way.end!] || []) {
      const w1 = this.store.way[1][i];
      let nd = 0;
      if (w1.nodes[0] === way.end) nd = w1.nodes[1];
      if (w1.nodes[w1.nodes.length - 1] === way.end) nd = w1.nodes[w1.nodes.length - 2];
      const angle = this.normalizeAngle(
        this.calcDirection(this.store.node[1][way.end!], this.store.node[1][nd]) - stangle
      ).toFixed(1);
      let main = this.waydata[i] ? 'main' : '';
      if (i === next) main = 'next';
      let direction = 'toward';
      if (w1.nodes[0] === way.end && (w1.tags['oneway'] === undefined || w1.tags['oneway'] !== '-1')) direction = 'away';
      else if (w1.nodes[w1.nodes.length - 1] === way.end && (w1.tags['oneway'] === undefined || w1.tags['oneway'] === '-1'))
        direction = 'away';

      if (main) {
        const from = i === id ? 'from' : '';
        out += `<div class="connects ${main} ${from}" style="transform:rotate(${angle}deg)">&nbsp;</div>`;
      } else {
        const title = this.listtags(w1);
        cntways++;
        connectsangle = Number(angle);
        connectsid = i;
        out += `<a href="https://www.openstreetmap.org/way/${i}" target="_blank"><div class="connects ${direction}" style="transform:rotate(${angle}deg)" title="Way ${i}\n${title}">&nbsp;</div></a>`;
      }
    }
    out += '</div>';

    const ends = this.endnodes[1][way.end!] || [];
    if (
      ends.length >= 3 &&
      cntways === 1 &&
      ((connectsangle > -160 && connectsangle < -20) || connectsangle > 200)
    ) {
      this.inspectLanes(this.store.way[1][connectsid]);
      out += '<div class="connectdestination">';
      const d = this.makeAllDestinations(connectsid, 1, id);
      for (const l of d) out += l;
      out += '</div>';
    }
    return out;
  }

  private makeShoulder(id: number, side: string): string {
    const obj = this.waydata[id];
    let o = '';
    const shoulder = obj.tags['shoulder'];
    const sr = obj.tags['shoulder:right'];
    const sl = obj.tags['shoulder:left'];
    if (!obj.reversed) {
      if (side === 'right') {
        if (shoulder === 'right' || shoulder === 'both' || sr === 'yes') o += '<div class="lane shoulder">&nbsp;</div>';
        if (((shoulder !== undefined && shoulder !== 'right' && shoulder !== 'both') || shoulder === 'no') && sr !== 'yes' || sr === 'no')
          o += '<div class="lane noshoulder" >&nbsp;</div>';
      } else {
        if (((shoulder !== undefined && shoulder !== 'left' && shoulder !== 'both') || shoulder === 'no') && sl !== 'yes' || sl === 'no') {
          o += '<div class="lane noshoulder">&nbsp;</div>';
          obj.lanes!.offset! -= 4;
        }
        if (shoulder === 'left' || shoulder === 'both' || sl === 'yes') {
          o += '<div class="lane shoulder" >&nbsp;</div>';
          obj.lanes!.offset! -= this.LANEWIDTH * 0.6;
        }
      }
    } else {
      if (side === 'right') {
        if (((shoulder !== undefined && shoulder !== 'left' && shoulder !== 'both') || shoulder === 'no') && sl !== 'yes' || sl === 'no')
          o += '<div class="lane noshoulder" >&nbsp;</div>';
        if (shoulder === 'left' || shoulder === 'both' || sl === 'yes') o += '<div class="lane shoulder">&nbsp;</div>';
      } else {
        if (shoulder === 'right' || shoulder === 'both' || sr === 'yes') {
          o += '<div class="lane shoulder" >&nbsp;</div>';
          obj.lanes!.offset! -= this.LANEWIDTH * 0.6;
        }
        if (((shoulder !== undefined && shoulder !== 'right' && shoulder !== 'both') || shoulder === 'no') && sr !== 'yes' || sr === 'no') {
          o += '<div class="lane noshoulder">&nbsp;</div>';
          obj.lanes!.offset! -= 4;
        }
      }
    }
    return o;
  }

  private makeSidewalk(id: number, side: string): string {
    const obj = this.waydata[id];
    let o = '';
    const sidewalk = obj.tags['sidewalk'];
    let l = '';
    let r = '';
    if (sidewalk === 'no' || sidewalk === 'none') {
      l = 'nosidewalk';
      r = 'nosidewalk';
    } else if (sidewalk === 'left') {
      l = 'sidewalk';
      r = 'nosidewalk';
    } else if (sidewalk === 'right') {
      l = 'nosidewalk';
      r = 'sidewalk';
    } else if (sidewalk === 'both') {
      l = 'sidewalk';
      r = 'sidewalk';
    } else if (sidewalk !== undefined) {
      l = 'nosidewalk';
      r = 'nosidewalk';
    }
    if ((obj.tags['sidewalk:left'] || '') === 'yes') l = 'sidewalk';
    if ((obj.tags['sidewalk:right'] || '') === 'yes') r = 'sidewalk';
    if ((obj.tags['sidewalk:both'] || '') === 'yes') {
      r = 'sidewalk';
      l = 'sidewalk';
    }

    let swlwidth = 4;
    let swrwidth = 4;
    if (!/^no/.test(l)) swlwidth = this.LANEWIDTH / 2;
    if (!/^no/.test(r)) swrwidth = this.LANEWIDTH / 2;
    const wl = obj.tags['sidewalk:left:width'] || obj.tags['sidewalk:both:width'] || obj.tags['sidewalk:width'];
    const wr = obj.tags['sidewalk:right:width'] || obj.tags['sidewalk:both:width'] || obj.tags['sidewalk:width'];
    if ((obj.tags['sidewalk:width'] !== undefined || obj.tags['sidewalk:left:width'] !== undefined || obj.tags['sidewalk:both:width'] !== undefined) && !/^no/.test(l))
      swlwidth = (this.LANEWIDTH / 4) * parseFloat(wl);
    if ((obj.tags['sidewalk:width'] !== undefined || obj.tags['sidewalk:right:width'] !== undefined || obj.tags['sidewalk:both:width'] !== undefined) && !/^no/.test(r))
      swrwidth = (this.LANEWIDTH / 4) * parseFloat(wr);

    if (r && ((side === 'right' && !obj.reversed) || (side === 'left' && obj.reversed))) {
      o += `<div class="lane ${r}" style='width:${swrwidth}px;' >&nbsp;</div>`;
    } else if (l && ((side === 'left' && !obj.reversed) || (side === 'right' && obj.reversed))) {
      o += `<div class="lane ${l}" style='width:${swlwidth}px;'>&nbsp;</div>`;
    }
    if (r && obj.reversed && side === 'right') obj.lanes!.offset! -= swrwidth;
    if (l && !obj.reversed && side === 'left') obj.lanes!.offset! -= swlwidth;
    return o;
  }

  private linkWay(id: number, arrow: string, style = 'navigation'): string {
    if (!this.opts.extendway) return '';
    if (arrow === 'up') arrow = '&#9650;';
    if (arrow === 'down') arrow = '&#9660;';
    return `<span class="${style}" data-wayid="${id}">${arrow}</span>`;
  }

  /** Record one way's length + coverage flags for the stats dashboard. */
  private collectStat(id: number, length: number): void {
    const t = this.waydata[id].tags;
    const has = (...keys: string[]) => keys.some((k) => t[k] !== undefined && t[k] !== '');
    const present: Record<Criterion, boolean> = {
      maxspeed: has('maxspeed', 'maxspeed:forward', 'maxspeed:backward', 'maxspeed:lanes'),
      lanes: has('lanes', 'lanes:forward', 'lanes:backward', 'lanes:both_ways'),
      turn: has('turn', 'turn:lanes', 'turn:lanes:forward', 'turn:lanes:backward'),
      surface: has('surface'),
      lit: has('lit'),
      oneway: has('oneway'),
      name: has('name'),
      ref: has('ref', 'int_ref'),
      width: has('width', 'width:lanes'),
      shoulder: has('shoulder', 'shoulder:left', 'shoulder:right', 'shoulder:both'),
      sidewalk: has('sidewalk', 'sidewalk:left', 'sidewalk:right', 'sidewalk:both'),
      structure: has('bridge', 'tunnel'),
      access: has('bicycle', 'foot', 'hgv', 'psv', 'bus', 'access', 'vehicle')
    };
    this.stats.push({
      id,
      name: t['name'] || '',
      ref: t['ref'] || '',
      length,
      oneway: t['oneway'] !== undefined && t['oneway'] !== 'no',
      maxspeed: parseSpeed(t),
      present
    });
  }

  private drawWay(id: number): string {
    const way = this.waydata[id];
    const t = way.tags;
    let out = '';
    const length = this.calcLength(id);
    this.totallength += length;
    this.collectStat(id, length);

    this.inspectLanes(way);
    const lanes = way.lanes!;

    const lat = this.nodedata[way.begin!].lat;
    const lon = this.nodedata[way.begin!].lon;

    // intersections along this segment (nodes shared with a crossing road)
    const wayCross: { label: string; lat: number; lon: number; major: boolean; hw: string }[] = [];
    for (let i = 0; i < way.nodes.length; i++) {
      const n = way.nodes[i];
      const roads = this.crossByNode[n];
      if (!roads || !roads.length) continue;
      const nd = this.nodedata[n];
      // our direction of travel through node n (for left/right of each branch)
      let heading = 0;
      if (i > 0) heading = this.compass(this.nodedata[way.nodes[i - 1]], nd);
      else if (i + 1 < way.nodes.length) heading = this.compass(nd, this.nodedata[way.nodes[i + 1]]);
      for (const r of roads) {
        const dir = this.crossingDir(r, n, heading);
        const arrow = dir === 'left' ? '←' : dir === 'right' ? '→' : '↑';
        wayCross.push({
          label: `${arrow} ${r.ref ? r.ref + ' ' : ''}${r.name || r.highway.replace(/_/g, ' ')}`,
          lat: nd?.lat,
          lon: nd?.lon,
          major: MAJOR_HW.has(r.highway),
          hw: r.highway
        });
      }
    }

    // record geometry for the Leaflet map (replaces generateMapJS)
    this.wayCoords[id] = {
      line: way.nodes.map((n) => [this.nodedata[n].lat, this.nodedata[n].lon] as [number, number]),
      begin: [lat, lon],
      crossings: wayCross.map((c) => ({ lat: c.lat, lon: c.lon, label: c.label }))
    };

    let name = t['name'] || '';
    if (t['bridge:name']) name += '<br>][ ' + t['bridge:name'];
    if (t['tunnel:name']) name += '<br>)( ' + t['tunnel:name'];
    if (!name) name = '&nbsp;';

    out += '<div class="way" >';
    if (this.opts.usePlacement) out += '<div class="middle">&nbsp;</div>';

    out += `<div class="label" data-way="${id}">`;
    out += `km ${(this.totallength / 1000).toFixed(1)}`;
    out += `<br><a name="${id}" href="https://www.openstreetmap.org/way/${id}" title="${this.listtags(way)}" >Way ${id}</a>`;
    out += `<br>${Math.round(length)}m`;
    out += `<br><a title="view on Mapillary" target="_blank" href="http://www.mapillary.com/app/?lat=${lat.toFixed(5)}&lng=${lon.toFixed(5)}&z=16">(M)</a>`;
    out += ` <a title="load in JOSM" target="_blank" href="${JOSM_BASE}/load_and_zoom?left=${(lon - 0.01).toFixed(5)}&right=${(lon + 0.01).toFixed(5)}&top=${(lat + 0.005).toFixed(5)}&bottom=${(lat - 0.005).toFixed(5)}&select=way${id}">(J)</a>`;
    out += ` <a title="load in level0 editor" target="_blank" href="http://level0.osmz.ru/?url=way/${id}!">(L)</a>`;
    out += ` <a title="edit in Rapid (iD)" target="_blank" href="https://rapideditor.org/edit#id=w${id}&map=18/${lat.toFixed(5)}/${lon.toFixed(5)}">(R)</a>`;
    out += ` <span class="normal" data-zoom="${id}" title="zoom map to this segment">(Z)</span>\n`;
    out += this.linkWay(id, '(V)', 'normal');
    out += '</div>\n';

    out += '<div class="info">';
    out += this.makeRef((t['ref'] || '') + ';' + (t['int_ref'] || ''));
    out += `<div style="clear:both;width:100%">${name}</div>`;
    if (wayCross.length) {
      const names = escapeEntities(wayCross.map((c) => c.label).join('\n'));
      // counts grouped by highway type, majors first then by frequency
      const byType: Record<string, number> = {};
      for (const c of wayCross) byType[c.hw] = (byType[c.hw] || 0) + 1;
      const parts = Object.entries(byType)
        .sort((a, b) => Number(MAJOR_HW.has(b[0])) - Number(MAJOR_HW.has(a[0])) || b[1] - a[1])
        .map(([k, v]) => `${v} ${k.replace(/_/g, ' ')}`)
        .join(' &middot; ');
      out += `<div class="xcount" title="${names}">&#10006; ${wayCross.length}: ${parts}</div>`;
    }
    out += '<div class="signs">';
    out += this.makeMaxspeed(id, 'maxspeed');
    out += this.makeMaxspeed(id, 'minspeed');
    out += this.makeSigns(way);
    if (this.opts.usenodes) out += this.makeNodeSigns(id);
    out += '</div></div>\n';

    const bridge = (t['bridge'] !== undefined ? 'bridge' : '') + (t['tunnel'] !== undefined ? ' tunnel' : '');

    lanes.destinations = this.makeAllDestinations(id, 0);

    const outputlanes: string[] = [];
    for (let i = 0; i < lanes.numlanes; i++) {
      const dir = lanes.list[i];
      const turns = lanes.turn?.[i] || '';
      const max = lanes.maxspeed?.[i] || '';
      const min = lanes.minspeed?.[i] || '';
      const width = lanes.width?.[i] || 0;
      const access = lanes.access?.[i] || '';
      const change = (lanes.change?.[i] || '') + ' ';
      let o = `<div class="lane ${dir} ${change}${access}" `;
      if (this.opts.lanewidth && width) o += `style="width:${width * this.LANEWIDTH / 4 - STROKEWIDTH * 2}px"`;
      o += '>';
      if (dir !== 'nolane') {
        o += this.makeTurns(turns, dir);
        if (lanes.destinations[i]) o += lanes.destinations[i];
        o += `<div class="signs" style="transform:skewX(-${lanes.tilt || 0}deg)">`;
        if (max) o += `<div class="max ${max === 'none' ? 'none' : ''}">${max === 'none' ? '' : max}</div>`;
        if (min && min !== 'none') o += `<div class="min">${min}</div>`;
        o += this.makeSigns(way, i);
        o += '</div>';
        if (width && !this.opts.lanewidth) o += `<div class="width">&#x21E0;${width.toFixed(1)}&#x21E2;</div>`;
      }
      o += '</div>';
      outputlanes.push(o);
    }

    outputlanes.unshift(this.makeShoulder(id, 'left'));
    outputlanes.push(this.makeShoulder(id, 'right'));
    outputlanes.unshift(this.makeSidewalk(id, 'left'));
    outputlanes.push(this.makeSidewalk(id, 'right'));

    out += `<div class="placeholder ${bridge}" style="transform:skewX(${lanes.tilt || 0}deg);margin-left:${lanes.offset}px">\n`;
    out += outputlanes.join('\n');
    out += '</div>';

    // one structured row for the native "sheet" editing view (rendered outside {@html})
    const dirs = new Set(lanes.list);
    const maxRaw = t['maxspeed'] || t['maxspeed:forward'] || '';
    // Thông tư 38 decision matrix (Bảng 2.1): category + legal default speeds.
    const highway = t['highway'] || '';
    const lanesNum = t['lanes'] ? parseInt(t['lanes'], 10) : NaN;
    const oneway = t['oneway'] !== undefined && t['oneway'] !== 'no';
    const dual = t['dual_carriageway'] === 'yes';
    const category: SheetRow['category'] =
      highway === 'motorway' || highway === 'motorway_link'
        ? 'motorway'
        : dual || (oneway && lanesNum >= 2) // đường đôi: median, or oneway with ≥2 lanes
          ? 'dual'
          : 'single';
    this.sheetRows.push({
      id,
      km: this.totallength / 1000,
      lengthM: Math.round(length),
      refHtml: this.makeRef((t['ref'] || '') + ';' + (t['int_ref'] || '')),
      nameHtml: name,
      max: maxRaw,
      hasMax: maxRaw !== '',
      dir:
        dirs.has('bothlane') || (dirs.has('forward') && dirs.has('backward'))
          ? 'both'
          : dirs.has('forward')
            ? 'forward'
            : dirs.has('backward')
              ? 'backward'
              : 'none',
      lat,
      lon,
      highway,
      lanes: Number.isNaN(lanesNum) ? null : lanesNum,
      oneway,
      dual,
      category,
      legalUrban: category === 'motorway' ? '120' : category === 'dual' ? '60' : '50',
      legalRural: category === 'motorway' ? '120' : category === 'dual' ? '90' : '80',
      ageDays: this.ageDays(id),
      tags: t
    });

    const beginnodetags = this.nodedata[way.begin!]?.tags || {};
    if (beginnodetags.highway === 'motorway_junction') {
      out += `<div class="sep"><div class="name">${beginnodetags.ref || ''} ${beginnodetags.name || ''}</div>`;
    } else {
      out += '<div class="sep">&nbsp;';
    }

    if (this.opts.adjacent && this.endnodes[1] && this.endnodes[1][way.end!]) {
      out += this.makeWaylayout(id, this.getBestNext(id));
    }

    out += '</div>';
    out += '</div>\n\n';
    return out;
  }

  // =========================================================================
  // render.pl main loop
  // =========================================================================

  /** Overpass query for ways adjacent to the end nodes of the loaded ways. */
  buildAdjacentQuery(): string {
    const ends = new Set<number>();
    for (const id of Object.keys(this.waydata).map(Number)) {
      if (this.waydata[id].end !== undefined) ends.add(this.waydata[id].end!);
    }
    const list = [...ends].join(',');
    return `[out:json][timeout:25];node(id:${list})->.ends;way(bn.ends)->.w;(.ends; .w; .w >;);out body qt;`;
  }

  /** organizeWays() must be called once before render() (and before any
   *  adjacent-way fetch). render() assumes it has already run. */
  render(start = 1): RenderResult {
    let startcnt = start;
    this.totalStartPoints = 0;
    this.totallength = 0;
    this.stats = [];
    this.sheetRows = [];
    let currid = 0;

    const ids = Object.keys(this.waydata)
      .map(Number)
      .sort((a, b) => a - b);

    for (const w of ids) {
      if (this.waydata[w].before === undefined) {
        this.totalStartPoints++;
        if (startcnt > 0) {
          currid = w;
          this.waydata[w].reversed = 0;
          startcnt--;
        }
      }
    }
    for (const w of ids) {
      if (this.waydata[w].after === undefined) {
        this.totalStartPoints++;
        if (startcnt > 0) {
          currid = w;
          this.waydata[w].reversed = 1;
          startcnt--;
        }
      }
    }

    let html = '';
    while (true) {
      const outarr: string[] = [];
      outarr.push(this.linkWay(currid, 'down'));
      while (true) {
        if (this.waydata[currid].used) break;
        this.waydata[currid].used = true;
        const w = this.waydata[currid];
        if (w.reversed) {
          [w.end, w.begin] = [w.begin, w.end];
          [w.after, w.before] = [w.before, w.after];
          w.nodes = [...w.nodes].reverse();
        }
        outarr.push(this.drawWay(currid));
        if (w.after === undefined) break;
        const nextid = this.getBestNext(currid);
        if (nextid === undefined) break;
        this.waydata[nextid].reversed = this.waydata[currid].end === this.waydata[nextid].end ? 1 : 0;
        currid = nextid;
      }
      outarr.push(this.linkWay(currid, 'up'));
      html += [...outarr].reverse().join('');

      currid = 0;
      for (const w of ids) {
        if (this.waydata[w].before === undefined && !this.waydata[w].used) currid = w;
      }
      if (currid === 0) {
        for (const w of ids) {
          if (!this.waydata[w].used) currid = w;
        }
      }
      if (currid === 0) break;
      html += '<hr>';
    }

    this.pairCarriageways(); // link divided-road carriageways now all geometry exists

    // flat export rows: computed fields up front, then every raw OSM tag on the way
    const exportRows = this.stats.map((s) => ({
      wayId: s.id,
      name: s.name,
      ref: s.ref,
      lengthKm: +(s.length / 1000).toFixed(3),
      oneway: s.oneway,
      maxspeedKmh: s.maxspeed ?? '',
      ...this.waydata[s.id].tags
    }));

    return {
      html,
      totalStartPoints: this.totalStartPoints,
      wayCoords: this.wayCoords,
      stats: this.stats,
      rawLengthKm: this.totallength / 1000,
      intersections: this.intersections,
      exportRows,
      sheetRows: this.sheetRows
    };
  }
}

// Overpass query builders (ported from render.pl). Ways are output with `out meta`
// so each carries its OSM `timestamp` (edit freshness); nodes stay `out` (body) so
// their tags survive for sign/junction rendering. `node(w.w)` pulls the ways' nodes.
const wayMetaTail = '.w out meta qt;node(w.w);out qt;';
export function wayQuery(id: string): string {
  return `[out:json][timeout:25];way(${id})->.w;${wayMetaTail}`;
}
function relRouteQuery(selector: string): string {
  return `[out:json][timeout:25];${selector}->.r;.r out body qt;way(r.r)->.w;${wayMetaTail}`;
}
export function relQuery(id: string): string {
  return relRouteQuery(`relation(${id})`);
}
export function relNameQuery(name: string): string {
  return relRouteQuery(`relation["name"="${name}"]`);
}
export function relRefQuery(ref: string): string {
  return relRouteQuery(`relation["ref"="${ref}"]`);
}
