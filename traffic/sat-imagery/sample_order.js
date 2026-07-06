#!/usr/bin/env node
// Bakes a per-hex PRIORITY score into data.js and the resulting fill order.
// Each candidate hex gets: priority = WD*density_percentile + WR*road_score + WK*key_area.
// The free-sample optimizer fills a partner's budget by descending priority
// (window.DATA.sample_order), then dissolves the picked cells into scene polygons.
//
//   density_percentile : rank of built_up_ratio (b) across candidates, 0..1
//   road_score         : top road class weight (motorway=1 .. tertiary=.15), 0 if none
//   key_area           : strategic bonus — island / maritime cell (1) else 0
//
// Tune the weights and key rule below. Run after export_static.py:
//   node traffic/sat-imagery/sample_order.js      (writes back into data.js)

const fs = require('fs');
const path = require('path');
const DATA = path.join(__dirname, 'data.js');

global.window = {};
require(DATA);
const D = window.DATA;
const F = D.fc.features;

const CAP = 2500;                 // cells baked (~ up to ~13,000 km²)
const WD = 0.6, WR = 0.3, WK = 0.1;
const ROADW = [1, 0.8, 0.6, 0.3, 0.15];   // by top-class idx: motorway..tertiary; -1 => 0

// candidates = the brief's buy-envelope: urban ≥10% built-up, OR a motorway/trunk/
// primary corridor cell, OR an island (key) cell. Keeps tier areas meaningful.
const cand = [];
for (let i = 0; i < F.length; i++) {
  const p = F[i].properties;
  if (p.b >= 0.10 || (p.c >= 0 && p.c <= 2) || p.i) cand.push(i);
}

// density percentile via sorted built-up ratios (fraction of candidates <= b)
const bs = cand.map(i => F[i].properties.b).sort((a, b) => a - b);
const pctl = v => { let lo = 0, hi = bs.length; while (lo < hi) { const m = (lo + hi) >> 1; if (bs[m] <= v) lo = m + 1; else hi = m; } return lo / bs.length; };

function priority(i) {
  const p = F[i].properties;
  const dens = pctl(p.b);
  const road = p.c >= 0 ? ROADW[p.c] : 0;
  const key = p.i ? 1 : 0;
  return WD * dens + WR * road + WK * key;
}

const scored = cand.map(i => [i, priority(i)]).filter(x => x[1] > 0);
scored.sort((a, b) => b[1] - a[1]);
const top = scored.slice(0, CAP);
const order = top.map(x => x[0]);
const pri = top.map(x => Math.round(x[1] * 1000) / 1000);

D.sample_order = order;
D.sample_pri = pri;

// --- priority tiers (for the selector): quantile bands over all scored cells -
const N = 5;                        // number of priority levels
const ringArea = ring => {          // spherical excess km²
  const R = 6371.0088, d = Math.PI / 180; let s = 0;
  for (let k = 0; k < ring.length - 1; k++) { const a = ring[k], b = ring[k + 1]; s += (b[0] - a[0]) * d * (2 + Math.sin(a[1] * d) + Math.sin(b[1] * d)); }
  return Math.abs(s * R * R / 2);
};
const BANDS = [0.75, 0.60, 0.45, 0.30, 0];   // lower score bound of P1..P5 (1=highest)
const tierOf = s => { for (let t = 0; t < BANDS.length; t++) if (s >= BANDS[t]) return t + 1; return 0; };
const htier = new Array(F.length).fill(0);
const tierKm2 = new Array(N + 1).fill(0);
const tierN = new Array(N + 1).fill(0);
scored.forEach(x => {
  const t = tierOf(x[1]);
  htier[x[0]] = t;
  tierKm2[t] += ringArea(F[x[0]].geometry.coordinates[0]);
  tierN[t]++;
});
D.htier = htier;
D.tier_km2 = tierKm2.map(v => Math.round(v));

// --- rewrite data.js: replace/append the two baked lines ---------------------
let src = fs.readFileSync(DATA, 'utf8');
for (const k of ['sample_order', 'sample_pri', 'htier', 'tier_km2'])
  src = src.replace(new RegExp('\\nwindow\\.DATA\\.' + k + '=.*?;\\n', 's'), '\n');
if (!src.endsWith('\n')) src += '\n';
src += 'window.DATA.sample_order=' + JSON.stringify(order) + ';\n';
src += 'window.DATA.sample_pri=' + JSON.stringify(pri) + ';\n';
src += 'window.DATA.htier=' + JSON.stringify(htier) + ';\n';
src += 'window.DATA.tier_km2=' + JSON.stringify(D.tier_km2) + ';\n';
fs.writeFileSync(DATA, src);

// --- self-check --------------------------------------------------------------
const dsc = order.every((_, k) => k === 0 || pri[k] <= pri[k - 1]);
const provs = new Set(order.map(i => F[i].properties.p)).size;
const withRoad = order.filter(i => F[i].properties.c >= 0).length;
const keyN = order.filter(i => F[i].properties.i).length;
console.log(`candidates=${cand.length} scored=${scored.length} baked=${order.length}`);
console.log(`pri[top]=${pri[0]} pri[last]=${pri[pri.length - 1]} descending=${dsc} provinces=${provs} with_road=${withRoad} key_cells=${keyN}`);
console.log('tiers (P1..P5):');
for (let t = 1; t <= N; t++) console.log(`  P${t}: ${tierN[t]} cells, ${D.tier_km2[t].toLocaleString()} km²  (cumulative ${D.tier_km2.slice(1, t + 1).reduce((a, b) => a + b, 0).toLocaleString()} km²)`);
console.assert(dsc, 'order not descending by priority');
console.assert(new Set(order).size === order.length, 'duplicate in order');
console.assert(htier.filter(t => t > 0).length === scored.length, 'tier count mismatch');
console.log('priority order + tiers baked into data.js');
