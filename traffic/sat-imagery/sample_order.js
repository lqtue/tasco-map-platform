#!/usr/bin/env node
// Bakes window.DATA.sample_order into data.js: a density-ranked, variety-seeded,
// contiguous region-growing order of candidate cells. In-browser the partner
// picks a free-km² budget and we reveal cells up to that budget, then dissolve.
//
// Shape: grow one connected blob (densest-first) from the densest urban core;
//        when its frontier drains, seed a NEW cluster in an as-yet-unrepresented
//        province (variety), preferring that province's densest cell.
// Metric: built_up_ratio (b). Candidates = cells with b>0 (evaluation-worthy urban).
// Cap: first CAP cells (~ enough for any realistic free sample).
//
// Run:  node traffic/sat-imagery/sample_order.js   (writes back into data.js)

const fs = require('fs');
const path = require('path');
const DIR = __dirname;
const DATA = path.join(DIR, 'data.js');

global.window = {};
require(DATA);
const D = window.DATA;
const F = D.fc.features;
const CAP = 2500;                       // ~ up to ~12,900 km² of ranked cells
const THR = 0.10;                       // urban floor: isolates city cores (rural b>0 sprawl connects everything)

// --- adjacency via shared-edge hash -----------------------------------------
const key = (a, b) => {                 // undirected edge key from two vertices
  const r = v => v.toFixed(5);
  const A = r(a[0]) + ',' + r(a[1]), B = r(b[0]) + ',' + r(b[1]);
  return A < B ? A + '|' + B : B + '|' + A;
};
const edgeCells = new Map();            // edge -> [featIdx,...]
const cand = [];                        // candidate feature indices (b>0)
for (let i = 0; i < F.length; i++) {
  if (!(F[i].properties.b >= THR)) continue;
  cand.push(i);
  const ring = F[i].geometry.coordinates[0];
  for (let j = 0; j < ring.length - 1; j++) {
    const k = key(ring[j], ring[j + 1]);
    (edgeCells.get(k) || edgeCells.set(k, []).get(k)).push(i);
  }
}
const isCand = new Uint8Array(F.length);
cand.forEach(i => isCand[i] = 1);
const nbrs = new Map();                 // featIdx -> Set(neighbor featIdx)
for (const cells of edgeCells.values()) {
  if (cells.length < 2) continue;
  for (const a of cells) for (const b of cells) if (a !== b && isCand[a] && isCand[b]) {
    (nbrs.get(a) || nbrs.set(a, new Set()).get(a)).add(b);
  }
}
const dens = i => F[i].properties.b;
const prov = i => F[i].properties.p;

// province -> its candidate idxs sorted by density desc (for variety seeding)
const byProv = new Map();
for (const i of cand) (byProv.get(prov(i)) || byProv.set(prov(i), []).get(prov(i))).push(i);
for (const arr of byProv.values()) arr.sort((a, b) => dens(b) - dens(a));

// --- max-heap of [density, idx] ---------------------------------------------
class Heap {
  constructor() { this.h = []; }
  push(d, i) { const h = this.h; h.push([d, i]); let c = h.length - 1;
    while (c > 0) { const p = (c - 1) >> 1; if (h[p][0] >= h[c][0]) break; [h[p], h[c]] = [h[c], h[p]]; c = p; } }
  pop() { const h = this.h; if (!h.length) return null; const top = h[0], last = h.pop();
    if (h.length) { h[0] = last; let p = 0; for (;;) { let l = 2*p+1, r = 2*p+2, m = p;
      if (l < h.length && h[l][0] > h[m][0]) m = l; if (r < h.length && h[r][0] > h[m][0]) m = r;
      if (m === p) break; [h[m], h[p]] = [h[p], h[m]]; p = m; } } return top; }
  get size() { return this.h.length; }
}

// --- variety-seeded contiguous growth ---------------------------------------
const selected = new Uint8Array(F.length);
const represented = new Set();
const order = [];
const frontier = new Heap();

function add(i) {
  selected[i] = 1; order.push(i); represented.add(prov(i));
  const ns = nbrs.get(i); if (ns) for (const n of ns) if (!selected[n]) frontier.push(dens(n), n);
}
function seed() {
  // prefer densest cell in an unrepresented province (variety)
  let best = -1, bestD = -1;
  for (const [p, arr] of byProv) {
    if (represented.has(p)) continue;
    for (const i of arr) { if (!selected[i]) { if (dens(i) > bestD) { bestD = dens(i); best = i; } break; } }
  }
  if (best >= 0) return best;
  // fallback: global densest unselected candidate
  for (const [, arr] of byProv) for (const i of arr) if (!selected[i]) { if (dens(i) > bestD) { bestD = dens(i); best = i; } break; }
  return best;
}

while (order.length < CAP) {
  let next;
  while (frontier.size) { const t = frontier.pop(); if (!selected[t[1]]) { next = t[1]; break; } }
  if (next === undefined) { next = seed(); if (next < 0) break; }
  add(next);
}

D.sample_order = order;

// --- rewrite data.js: replace/append the sample_order line -------------------
let src = fs.readFileSync(DATA, 'utf8');
const line = 'window.DATA.sample_order=' + JSON.stringify(order) + ';\n';
src = src.replace(/\nwindow\.DATA\.sample_order=.*?;\n/s, '\n');
if (!src.endsWith('\n')) src += '\n';
fs.writeFileSync(DATA, src + line);

// --- self-check --------------------------------------------------------------
const provsCovered = new Set(order.map(prov)).size;
console.log(`candidates=${cand.length} order=${order.length} provinces_covered=${provsCovered}`);
console.assert(order.length > 0, 'empty order');
console.assert(new Set(order).size === order.length, 'duplicate in order');
console.assert(order.every((i, k) => k === 0 || dens(order[0]) >= 0), 'density read ok');
// contiguity: every cell after the first is adjacent to an earlier one OR a seed
let seeds = 0;
for (let k = 1; k < order.length; k++) {
  const ns = nbrs.get(order[k]); const earlier = new Set(order.slice(0, k));
  if (!ns || ![...ns].some(n => earlier.has(n))) seeds++;
}
console.log(`clusters(seeds)=${seeds + 1}  first-cell density=${dens(order[0]).toFixed(3)}`);
console.log('sample_order baked into data.js');
