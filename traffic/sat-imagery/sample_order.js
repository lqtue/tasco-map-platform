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

// candidates = any evaluation-worthy hex: built-up, on a road, or a key (island) cell
const cand = [];
for (let i = 0; i < F.length; i++) {
  const p = F[i].properties;
  if (p.b > 0 || p.c >= 0 || p.i) cand.push(i);
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

// --- rewrite data.js: replace/append the two baked lines ---------------------
let src = fs.readFileSync(DATA, 'utf8');
src = src.replace(/\nwindow\.DATA\.sample_order=.*?;\n/s, '\n')
         .replace(/\nwindow\.DATA\.sample_pri=.*?;\n/s, '\n');
if (!src.endsWith('\n')) src += '\n';
src += 'window.DATA.sample_order=' + JSON.stringify(order) + ';\n';
src += 'window.DATA.sample_pri=' + JSON.stringify(pri) + ';\n';
fs.writeFileSync(DATA, src);

// --- self-check --------------------------------------------------------------
const dsc = order.every((_, k) => k === 0 || pri[k] <= pri[k - 1]);
const provs = new Set(order.map(i => F[i].properties.p)).size;
const withRoad = order.filter(i => F[i].properties.c >= 0).length;
const keyN = order.filter(i => F[i].properties.i).length;
console.log(`candidates=${cand.length} scored=${scored.length} baked=${order.length}`);
console.log(`pri[top]=${pri[0]} pri[last]=${pri[pri.length - 1]} descending=${dsc} provinces=${provs} with_road=${withRoad} key_cells=${keyN}`);
console.assert(dsc, 'order not descending by priority');
console.assert(new Set(order).size === order.length, 'duplicate in order');
console.log('priority order baked into data.js');
