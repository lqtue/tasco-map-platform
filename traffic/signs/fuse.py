"""Bayesian maxspeed fusion — merge every source into one value + confidence.

Each data source (the current OSM tag, our triangulated signs, Mapillary's own
detector, Waze, any other app) is a *noisy sensor* of one hidden truth: the real
maxspeed of a road segment. This fuses them per OSM way:

    P(V=v | obs) ∝ Prior(v) · Π_o  L(obs_o | V=v) ^ w_o

  - Prior(v)  = the Thông tư 38 legal default for the way's morphology (a coarse
                version here; upgrade path = wiki/02-bang-quyet-dinh-theo-luat.md).
  - L(·)      = a per-source confusion model parameterised by source reliability.
  - w_o       = how much the observation counts: source trust × freshness, with a
                penalty for sign images older than the segment's last OSM edit
                (a rebuilt/retagged road supersedes an old drive-by).

Output per way: predicted value, confidence (posterior of the winner), the
runner-up + margin, and the observations that drove it. The architecture
invariant: *AI detects, rules/graph reason* — sources only emit observations;
this file does the reasoning (RoadTagger, He et al. 2020).

Adding a source = drop a parquet/CSV of observations (lon,lat,value,source[,
confidence,observed_at]) via --extra and optionally register its trust in
SOURCE_TRUST. Waze, MaxBit, a future GSV crawl all plug in the same way.

Usage:
  python3 traffic/signs/fuse.py --selfcheck                      # no network
  MAPILLARY_TOKEN=… python3 traffic/signs/fuse.py --ref QL.51 \
      --signs traffic/signs/data/ql51_signs.parquet \
      --extra waze:/path/waze_speeds.parquet
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

import triangulate as tri
from compare_osm import _ms_int, _seg_dist_m, enrich_maxspeed_age, fetch_route_ways

DATA = Path(__file__).resolve().parent / "data"
NOW_MS = time.time() * 1000.0

# allowed posted speeds (VN); the support set also absorbs any observed value
VALUES = [30, 40, 50, 60, 70, 80, 90, 100, 110, 120]

# base P(source reports the truth). Tunable — these are the knobs that encode
# "trust our multi-view sign more than Waze". Unknown sources get DEFAULT_TRUST.
SOURCE_TRUST = {
    "osm": 0.80,             # current OSM tag — usually right, but can be stale
    "mapillary_sign": 0.85,  # our own triangulated, multi-view sign
    "mapillary_point": 0.70, # Mapillary's own (Euro-trained) detector
    "waze": 0.65,            # lookup-only reference
}
DEFAULT_TRUST = 0.60
HALFLIFE_Y = 6.0             # an observation's weight halves every 6 years
SUPERSEDED_PENALTY = 0.25    # a sign older than the segment's OSM edit
SIGMA_KMH = 8.0             # how tightly a posted value supports nearby speeds
CONF_TEMP = 1.2            # softens naive-Bayes overconfidence (calibration knob)
PRIOR_BASE = 0.7          # prior peakedness: a *weak* default that picks the legal
                          # value only with no evidence — must not override a lone tag


# --- legal prior (Thông tư 38, coarse) -------------------------------------
def legal_default(way):
    """Coarse TT38 default speed (km/h) from morphology.
    ponytail: class+divided heuristic — upgrade to the full decision matrix
    (built-up detection + wiki/02-bang-quyet-dinh-theo-luat.md) when needed."""
    hw = (way.get("highway") or "").split("_")[0]
    t = way.get("tags") or {}
    divided = (t.get("oneway") in ("yes", "-1", "true", "1")
               or t.get("dual_carriageway") == "yes" or hw == "motorway")
    if hw == "motorway":
        return 120
    if hw in ("trunk", "primary"):
        return 90 if divided else 80
    if hw == "secondary":
        return 80 if divided else 70
    return 60


def prior(support, default):
    """Soft distribution peaked on the legal default (mass decays with |Δspeed|).
    Deliberately weak (PRIOR_BASE near 1): it should decide only when there is no
    observation, never outvote a single explicit tag or sign."""
    w = {v: PRIOR_BASE ** (abs(v - default) / 10.0) for v in support}
    z = sum(w.values())
    return {v: w[v] / z for v in support}


# --- per-observation likelihood + weight -----------------------------------
def reliability(o):
    """P(report = truth) for one observation; sign quality nudges it."""
    r = SOURCE_TRUST.get(o["source"], DEFAULT_TRUST)
    if o["source"] == "mapillary_sign":
        r += 0.02 * max(0, o.get("n_views", 2) - 2)
        if o.get("spread", 0) > 5:
            r -= 0.05
    return max(0.5, min(0.97, r))


def _age_days(ms):
    if ms is None or (isinstance(ms, float) and math.isnan(ms)):
        return None
    return max(0.0, (NOW_MS - ms) / 86400000.0)


def weight(o, osm_edit_ms):
    """How much this observation counts: freshness decay × supersession penalty."""
    age = _age_days(o.get("obs_date_ms"))
    w = 0.5 ** (age / 365.0 / HALFLIFE_Y) if age is not None else 0.6
    if (o["source"].startswith("mapillary_sign") and osm_edit_ms
            and o.get("obs_date_ms") and o["obs_date_ms"] < osm_edit_ms):
        w *= SUPERSEDED_PENALTY
    return w * o.get("trust_mult", 1.0)


def _hit_kernel(supp, v_o):
    """A posted value v_o supports nearby speeds too (sensor/rounding spread),
    so adjacent values stay competitive — this is what keeps the posterior from
    collapsing to a hard 1.0 on a single reading."""
    k = {v: math.exp(-(((v - v_o) / SIGMA_KMH) ** 2)) for v in supp}
    z = sum(k.values())
    return {v: k[v] / z for v in supp}


def fuse(observations, default, support=None):
    """Naive-Bayes fuse observations against the legal prior.
    Returns (pred, confidence, runner_up, margin, posterior dict)."""
    supp = sorted(set((support or VALUES)) | {o["value"] for o in observations if o["value"]})
    logp = {v: math.log(p) for v, p in prior(supp, default).items()}
    osm_edit = next((o["obs_date_ms"] for o in observations if o["source"] == "osm"), None)
    miss = 1.0 / len(supp)
    for o in observations:
        if o["value"] is None:
            continue
        r = reliability(o)
        w = weight(o, osm_edit)
        hk = _hit_kernel(supp, o["value"])
        for v in supp:
            logp[v] += w * math.log(r * hk[v] + (1.0 - r) * miss)
    # temperature softens NB's known overconfidence into a calibrated score
    m = max(logp.values())
    post = {v: math.exp((lp - m) / CONF_TEMP) for v, lp in logp.items()}
    z = sum(post.values())
    post = {v: p / z for v, p in post.items()}
    ranked = sorted(post.items(), key=lambda kv: -kv[1])
    pred, conf = ranked[0]
    runner, second = (ranked[1] if len(ranked) > 1 else (None, 0.0))
    return pred, conf, runner, conf - second, post


# --- assemble observations per way -----------------------------------------
def _ways_enu(ways, lon0, lat0):
    return [(w["id"], [tri.enu(lon, lat, lon0, lat0) for lon, lat in w["line"]]) for w in ways]


def _nearest_way(pt, ways_enu):
    best_id, best_d = None, math.inf
    for wid, pts in ways_enu:
        for a, b in zip(pts, pts[1:]):
            d = _seg_dist_m(pt, a, b)
            if d < best_d:
                best_d, best_id = d, wid
    return best_id, best_d


def snap_points(df, ways_enu, lon0, lat0, source, max_m=30.0):
    """Turn a points DataFrame (lon,lat,value[,n_views,ray_spread_m,obs_date_ms,
    confidence,observed_at]) into per-way observation dicts."""
    by_way: dict[int, list] = {}
    for r in df.itertuples():
        wid, d = _nearest_way(tri.enu(r.lon, r.lat, lon0, lat0), ways_enu)
        if d > max_m:
            continue
        o = {
            "source": source,
            "value": _ms_int(getattr(r, "value", None)),
            "n_views": int(getattr(r, "n_views", 0) or 0),
            "spread": float(getattr(r, "ray_spread_m", 0.0) or 0.0),
            "obs_date_ms": _obs_ms(r),
            "trust_mult": float(getattr(r, "confidence", 1.0) or 1.0),
        }
        if o["value"] is not None:
            by_way.setdefault(wid, []).append(o)
    return by_way


def _obs_ms(r):
    """epoch ms from obs_date_ms (signs) or observed_at (epoch ms or ISO string)."""
    v = getattr(r, "obs_date_ms", None)
    if v is not None and not (isinstance(v, float) and math.isnan(v)):
        return float(v)
    oa = getattr(r, "observed_at", None)
    if oa is None:
        return None
    try:
        return float(oa)
    except (TypeError, ValueError):
        from compare_osm import _iso_ms
        try:
            return _iso_ms(str(oa))
        except Exception:
            return None


# --- self-check ------------------------------------------------------------
def _demo():
    """Posterior must behave: fresh strong signs override a stale OSM tag;
    agreeing sources give high confidence; conflicting sources give low."""
    yr = 365 * 86400000.0
    fresh, old = NOW_MS - 0.5 * yr, NOW_MS - 8 * yr

    # 1. stale OSM=60 vs two fresh multi-view 80 signs → predict 80, confident
    obs = [
        {"source": "osm", "value": 60, "obs_date_ms": old},
        {"source": "mapillary_sign", "value": 80, "n_views": 6, "spread": 0.1, "obs_date_ms": fresh},
        {"source": "mapillary_sign", "value": 80, "n_views": 5, "spread": 0.2, "obs_date_ms": fresh},
    ]
    pred, conf, *_ = fuse(obs, default=90)
    assert pred == 80 and conf > 0.6, f"expected 80 to win, got {pred}@{conf:.2f}"
    print(f"[1] stale OSM 60 overridden by fresh signs → {pred} @ {conf:.2f}")

    # 2. agreement: OSM=90 fresh + a fresh 90 sign → confident, actionable (≥0.85)
    pred, conf, *_ = fuse([
        {"source": "osm", "value": 90, "obs_date_ms": fresh},
        {"source": "mapillary_sign", "value": 90, "n_views": 4, "spread": 0.3, "obs_date_ms": fresh},
    ], default=90)
    assert pred == 90 and conf > 0.85, f"expected confident 90, got {pred}@{conf:.2f}"
    print(f"[2] sources agree → {pred} @ {conf:.2f}")

    # 3. conflict: fresh waze 100 vs fresh sign 80 → uncertain (small margin)
    pred, conf, runner, margin, _ = fuse([
        {"source": "waze", "value": 100, "obs_date_ms": fresh},
        {"source": "mapillary_sign", "value": 80, "n_views": 3, "spread": 0.4, "obs_date_ms": fresh},
    ], default=90)
    assert margin < 0.35 and conf < 0.7, f"conflict should be uncertain, got @{conf:.2f} m{margin:.2f}"
    print(f"[3] conflicting sources → {pred} @ {conf:.2f} (runner {runner}, margin {margin:.2f})")
    print("self-check OK")


# --- QL.51 runner ----------------------------------------------------------
def _cached_ways(ref, bbox):
    """Fetch the route's OSM ways once and cache to data/ (Overpass is slow and
    flaky; re-fetching 300+ ways every run is wasteful). Delete the json to refresh."""
    import json
    cache = DATA / f"{ref.replace('.', '_')}_ways.json"
    if cache.exists():
        return json.loads(cache.read_text())
    ways = fetch_route_ways(ref, bbox)
    if ways:
        DATA.mkdir(exist_ok=True)
        cache.write_text(json.dumps(ways))
    return ways


def run(ref, signs_path, extras, bbox):
    ways = _cached_ways(ref, bbox)
    if not ways:
        print(f"no OSM ways for {ref}", file=sys.stderr)
        return 1
    # freshness of the maxspeed *value* (not the way's last touch) — so a
    # teammate's geometry edit doesn't make a years-old speed look fresh
    enrich_maxspeed_age(ways, DATA / f"{ref.replace('.', '_')}_msage.json")
    lon0 = float(np.mean([lon for w in ways for lon, _ in w["line"]]))
    lat0 = float(np.mean([lat for w in ways for _, lat in w["line"]]))
    wenu = _ways_enu(ways, lon0, lat0)

    # gather per-way observations from each source
    per_way: dict[int, list] = {w["id"]: [] for w in ways}
    if signs_path and Path(signs_path).exists():
        sdf = pd.read_parquet(signs_path)
        for wid, obs in snap_points(sdf, wenu, lon0, lat0, "mapillary_sign").items():
            per_way[wid].extend(obs)
        print(f"signs: {len(sdf)} → snapped to {sum(1 for o in per_way.values() if o)} ways")
    for source, path in extras:
        edf = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
        for wid, obs in snap_points(edf, wenu, lon0, lat0, source).items():
            per_way[wid].extend(obs)
        print(f"{source}: {len(edf)} extra observations merged")

    rows = []
    for w in ways:
        obs = list(per_way[w["id"]])
        osm_v = _ms_int(w["maxspeed"])
        if osm_v is not None:
            obs.append({"source": "osm", "value": osm_v,
                        "obs_date_ms": w.get("ms_since_ms") or w["edit_ms"]})
        default = legal_default(w)
        pred, conf, runner, margin, _ = fuse(obs, default)
        rows.append({
            "way_id": w["id"], "highway": w["highway"], "osm_maxspeed": osm_v,
            "legal_default": default, "n_obs": len(obs),
            "predicted": pred, "confidence": round(conf, 3),
            "runner_up": runner, "margin": round(margin, 3),
            "changes_osm": osm_v is not None and pred != osm_v,
            "fills_osm": osm_v is None,
        })
    out = pd.DataFrame(rows)
    DATA.mkdir(exist_ok=True)
    out.to_parquet(DATA / "ql51_fused.parquet", index=False)

    hi = out[out["confidence"] >= 0.85]
    print(f"\nfused {len(out)} ways · {len(hi)} high-confidence (≥0.85)")
    print(f"  predictions changing the current OSM value: {int(out['changes_osm'].sum())}")
    print(f"  filling a missing OSM maxspeed: {int(out['fills_osm'].sum())}")
    chg = out[out["changes_osm"] & (out["confidence"] >= 0.85)].sort_values("confidence", ascending=False)
    if len(chg):
        print("\nhigh-confidence changes vs OSM (way: osm → predicted @conf, n_obs):")
        for r in chg.head(20).itertuples():
            print(f"  way {r.way_id}: {r.osm_maxspeed} → {r.predicted} @ {r.confidence} ({r.n_obs} obs)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="QL.51")
    ap.add_argument("--bbox", default="10.34,106.79,10.97,107.12", help="S,W,N,E search box")
    ap.add_argument("--signs", default=str(DATA / "ql51_signs.parquet"),
                    help="triangulated signs parquet (from compare_osm.py)")
    ap.add_argument("--extra", action="append", default=[], metavar="SOURCE:PATH",
                    help="extra observations, e.g. waze:waze.parquet (repeatable)")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()
    if args.selfcheck:
        _demo()
        return 0
    extras = []
    for spec in args.extra:
        source, _, path = spec.partition(":")
        if not path:
            print(f"--extra must be SOURCE:PATH, got {spec!r}", file=sys.stderr)
            return 2
        extras.append((source, path))
    return run(args.ref, args.signs, extras, args.bbox)


if __name__ == "__main__":
    sys.exit(main())
