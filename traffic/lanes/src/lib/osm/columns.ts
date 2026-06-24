// Sheet columns + presets for the maxspeed editing view.
// Rows are always rendered in this canonical order, filtered to the enabled keys —
// so a preset is just a membership set, no ordering logic needed.

export const COLUMNS = [
  { key: 'way', label: 'Way', width: '82px' },
  { key: 'length', label: 'Length', width: '78px' },
  { key: 'name', label: 'Name', width: 'minmax(120px,1fr)' },
  { key: 'class', label: 'Class', width: '74px' },
  { key: 'lanes', label: 'Lanes', width: '50px' },
  { key: 'oneway', label: '1-way', width: '50px' },
  { key: 'dual', label: 'Dual', width: '48px' },
  { key: 'maxspeed', label: 'Speed', width: '82px' },
  { key: 'suggest', label: 'Legal U/R', width: '96px' },
  { key: 'tools', label: 'Tools', width: '156px' }
] as const;

export type ColKey = (typeof COLUMNS)[number]['key'];

// default preset = the Thông tư 38 decision-tree inputs (morphology) + current speed
// + the computed legal default, so an editor can confirm against street-view evidence.
export const PRESETS: Record<string, ColKey[]> = {
  'Max speed': ['way', 'name', 'lanes', 'oneway', 'dual', 'maxspeed', 'suggest', 'tools'],
  Names: ['way', 'length', 'name', 'maxspeed', 'tools'],
  Compact: ['way', 'name', 'maxspeed', 'tools']
};

export const DEFAULT_PRESET = 'Max speed';

// look up a column's label + width; unknown keys are raw OSM tags (vehicle speeds, etc.)
const FIXED = new Map(COLUMNS.map((c) => [c.key as string, c]));
export function colDef(key: string): { key: string; label: string; width: string } {
  return FIXED.get(key) ?? { key, label: key, width: 'minmax(72px,auto)' };
}

// common VN speed-limit values for the inline editor (blank = clear, none = no limit)
export const SPEEDS = ['', 'none', '30', '40', '50', '60', '70', '80', '90', '100', '110', '120'];
