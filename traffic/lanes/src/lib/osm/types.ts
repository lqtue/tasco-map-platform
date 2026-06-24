// Data model ported from OSMData.pm / OSMLanes.pm

export type Tags = Record<string, string>;

export interface Lanes {
  fwd: number;
  bck: number;
  both: number;
  none: number;
  list: string[]; // per-lane direction: forward/backward/bothlane/nolane
  numlanes: number;
  // per-lane string arrays (one entry per lane), filled by getLaneTags
  turn?: string[];
  maxspeed?: string[];
  minspeed?: string[];
  bicycle?: string[];
  bus?: string[];
  psv?: string[];
  foot?: string[];
  access?: string[];
  vehicle?: string[];
  hgv?: string[];
  change?: string[];
  width?: number[];
  destinations?: string[];
  // destination component arrays (keys stripped of ':' and '_')
  [k: string]: unknown;
  // geometry
  haswidth?: number;
  totalwidth?: number;
  offset?: number;
  offend?: number;
  tilt?: number;
}

export interface Way {
  id: number;
  tags: Tags;
  nodes: number[];
  timestamp?: string; // OSM last-edit time (only present when the query uses `out meta`)
  begin?: number;
  end?: number;
  before?: number[];
  after?: number[];
  reversed?: 0 | 1;
  used?: boolean;
  lanes?: Lanes;
}

export interface OsmNode {
  id: number;
  tags: Tags;
  lat: number;
  lon: number;
}

export interface Store {
  way: Record<number, Way>[];
  node: Record<number, OsmNode>[];
  rel: Record<number, any>[];
}

export interface Options {
  country: string;
  usePlacement: boolean;
  adjacent: boolean;
  lanewidth: boolean;
  usenodes: boolean;
  extendway: boolean;
  intersections: boolean;
}

// a highway that crosses our road, and where
export interface CrossRoad {
  id: number;
  name: string;
  ref: string;
  highway: string;
}

export interface Intersection {
  nodeId: number;
  lat: number;
  lon: number;
  roads: CrossRoad[];
}

// which coverage criteria are present on a way (length-weighted in the dashboard)
export type Criterion =
  | 'maxspeed'
  | 'lanes'
  | 'turn'
  | 'surface'
  | 'lit'
  | 'oneway'
  | 'name'
  | 'ref'
  | 'width'
  | 'shoulder'
  | 'sidewalk'
  | 'structure'
  | 'access';

export interface WayStat {
  id: number;
  name: string;
  ref: string;
  length: number; // metres
  oneway: boolean;
  maxspeed: number | null; // km/h, numeric where parseable
  present: Record<Criterion, boolean>;
}

export interface RelationMeta {
  name: string;
  ref: string;
  wikidata: string;
}

// one search dispatched from the SearchPanel module to the page orchestrator
export interface SearchRequest {
  query: string;
  start: number;
  opts: Options;
}

// per-way geometry handed to the MapView module for preview/zoom
export interface WayGeom {
  line: [number, number][];
  begin: [number, number];
  crossings?: { lat: number; lon: number; label: string }[];
  pairId?: number; // opposing carriageway of a divided road, if detected
}

// one flat row per drawn way for CSV/JSON export: computed fields + all raw OSM tags
export type ExportRow = Record<string, string | number | boolean>;

// one row for the single-lane editing "sheet" view (rendered natively, not via {@html})
export interface SheetRow {
  id: number;
  km: number; // cumulative km at the end of this segment
  lengthM: number;
  refHtml: string; // pre-rendered route shields (reuses makeRef + CSS)
  nameHtml: string; // road name (may carry <br> for bridge/tunnel names)
  max: string; // raw maxspeed value ('' = missing, 'none' = explicit no-limit)
  hasMax: boolean;
  dir: 'forward' | 'backward' | 'both' | 'none'; // for the lane-colour legend
  lat: number; // segment begin, for the editor deep-links
  lon: number;
  // Thông tư 38 decision-tree inputs + computed legal default (the maxspeed preset)
  highway: string;
  lanes: number | null;
  oneway: boolean;
  dual: boolean; // dual_carriageway=yes
  category: 'motorway' | 'dual' | 'single'; // đường đôi vs đơn (matrix Bảng 2.1)
  legalUrban: string; // legal default maxspeed if in a built-up zone (km/h)
  legalRural: string; // legal default maxspeed outside built-up (motorcar value)
  ageDays: number | null; // days since the way's last OSM edit (null if no timestamp in the data)
  tags: Tags; // raw OSM tags, so any tag (vehicle speeds, node attrs…) can be a column
}

export interface RenderResult {
  html: string;
  totalStartPoints: number;
  // map of way id -> polyline coordinates, begin marker, intersection points
  wayCoords: Record<number, WayGeom>;
  stats: WayStat[];
  rawLengthKm: number;
  intersections: Intersection[];
  exportRows: ExportRow[];
  sheetRows: SheetRow[];
}
