"""Triangulate signs along one named route and compare to OSM maxspeed.

End-to-end QA run for the self-crawl pipeline on a real road (default QL.51):
  1. pull the route's ways (geometry + maxspeed) from OSM via Overpass,
  2. crawl Mapillary speed-sign detections along *only that corridor*,
  3. triangulate each sign (triangulate.py) and score vs the Mapillary ref,
  4. snap each triangulated sign to the nearest OSM section and compare the
     observed speed to the section's `maxspeed` tag.

Output: where OSM agrees with the signs on the ground, where it disagrees, and
where OSM has no maxspeed but a sign exists (the enrichment worklist).

Usage:
  MAPILLARY_TOKEN=MLY|... python3 traffic/signs/compare_osm.py --ref QL.51
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

import triangulate as tri
from detections_pull import filter_recent, pull_observations, triangulate_observations

DATA = Path(__file__).resolve().parent / "data"
TILE_DEG = 0.02
OVERPASS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
# corridor search box (S,W,N,E) keeps the ref regex from matching same-numbered
# roads elsewhere; default covers Biên Hòa → Vũng Tàu (QL.51).
DEFAULT_BBOX = "10.34,106.79,10.97,107.12"


def overpass(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for ep in OVERPASS:
        try:
            req = urllib.request.Request(ep, data=data, headers={"User-Agent": "tasco-signs/0.1"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001 - try the next mirror
            last = e
    raise RuntimeError(f"all Overpass mirrors failed: {last}")


def fetch_route_ways(ref, bbox):
    """OSM ways carrying `ref` in the corridor bbox, with geometry + maxspeed.
    The regex matches `ref` as a whole token (handles multi-ref `QL.1;QL.51`)
    and excludes suffixed siblings like QL.51C."""
    esc = re.escape(ref)
    q = (
        f'[out:json][timeout:180];'
        f'way[highway][ref~"{esc}($|[^0-9A-Za-z])"]({bbox});'
        f'out meta geom;'  # meta -> per-way `timestamp` (last edit)
    )
    els = overpass(q).get("elements", [])
    ways = []
    for e in els:
        g = e.get("geometry")
        if not g:
            continue
        ways.append({
            "id": e["id"],
            "maxspeed": e["tags"].get("maxspeed"),
            "highway": e["tags"].get("highway"),
            "tags": e["tags"],            # morphology (lanes/oneway/dual…) for the legal prior
            "edit_ms": _iso_ms(e.get("timestamp")),
            "line": [(p["lon"], p["lat"]) for p in g],
        })
    return ways


def _iso_ms(ts):
    """ISO8601 OSM timestamp -> epoch ms (matches Mapillary captured_at units)."""
    if not ts:
        return None
    from datetime import datetime
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000.0


OSM_HISTORY = "https://api.openstreetmap.org/api/0.6/way/{}/history.json"


def maxspeed_since_ms(way_id):
    """Epoch ms when the way's CURRENT maxspeed value was last *set*, from OSM
    version history. This is the real freshness of the speed — a geometry-only
    edit (node move, way split) that merely carried the tag along does NOT count.
    None if the way has no maxspeed now, or the history fetch fails."""
    try:
        req = urllib.request.Request(OSM_HISTORY.format(way_id),
                                     headers={"User-Agent": "tasco-signs/0.1"})
        with urllib.request.urlopen(req, timeout=30) as r:
            els = json.loads(r.read()).get("elements", [])
    except Exception:
        return None
    last_change, prev = None, object()  # sentinel ≠ any tag value (incl. None)
    for v in sorted(els, key=lambda e: e.get("version", 0)):
        ms = (v.get("tags") or {}).get("maxspeed")
        if ms != prev:                  # value transitioned at this version
            last_change = v.get("timestamp")
        prev = ms
    if prev is None:                    # current version carries no maxspeed
        return None
    return _iso_ms(last_change)


def enrich_maxspeed_age(ways, cache_path, pause=0.1):
    """Set each way's `ms_since_ms` (maxspeed last-changed time) from OSM history,
    caching per way id so the ~one-call-per-way cost is paid once. Falls back to
    the way's last-edit time when history is unavailable."""
    cache = {}
    p = Path(cache_path)
    if p.exists():
        cache = json.loads(p.read_text())
    todo = [w for w in ways if str(w["id"]) not in cache]
    if todo:
        print(f"maxspeed-age: querying OSM history for {len(todo)} ways…")
    for i, w in enumerate(todo, 1):
        cache[str(w["id"])] = maxspeed_since_ms(w["id"]) if w.get("maxspeed") else None
        time.sleep(pause)
        if i % 50 == 0:
            print(f"  {i}/{len(todo)}", flush=True)
    if todo:
        p.write_text(json.dumps(cache))
    for w in ways:
        w["ms_since_ms"] = cache.get(str(w["id"])) or w.get("edit_ms")
    return ways


def corridor_tiles(ways, step):
    """Tiles (w,s,e,n) the route passes through — skips empty off-corridor sea/
    field tiles so the Mapillary crawl stays bounded to the road."""
    keys = set()
    for w in ways:
        for lon, lat in w["line"]:
            keys.add((math.floor(lon / step), math.floor(lat / step)))
    return [(c * step, r * step, c * step + step, r * step + step) for (c, r) in keys]


def _seg_dist_m(pt, a, b):
    """Distance (m) from ENU point pt to segment a-b."""
    ab = b - a
    L2 = float(ab @ ab)
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, float((pt - a) @ ab) / L2))
    return float(np.linalg.norm(pt - (a + t * ab)))


def _ms_int(s):
    """Leading integer of an OSM maxspeed value, or None."""
    if not s:
        return None
    m = re.match(r"\s*(\d+)", str(s))
    return int(m.group(1)) if m else None


def _day(ms):
    """epoch ms -> YYYY-MM-DD (or '?')."""
    if ms is None or (isinstance(ms, float) and math.isnan(ms)):
        return "?"
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000.0, timezone.utc).strftime("%Y-%m-%d")


def compare(signs, ways, lon0, lat0, max_road_m=30.0):
    """Snap each triangulated sign to the nearest OSM section and classify it,
    using the *relative* timing of the sign observation vs the section's last
    OSM edit. A sign is only trustworthy evidence when it was observed AFTER the
    segment's last edit; if OSM was edited later (e.g. a rebuild/retag), the sign
    image may be obsolete. Adds: dist_road_m, osm_maxspeed, osm_edit_date,
    sign_obs_date, sign_newer, verdict."""
    segs = []
    for w in ways:
        pts = [tri.enu(lon, lat, lon0, lat0) for lon, lat in w["line"]]
        # the maxspeed's own age (when the value was last set), NOT the way's
        # last-touch time — a geometry edit must not look like a fresh speed
        edit = w.get("ms_since_ms") or w["edit_ms"]
        for a, b in zip(pts, pts[1:]):
            segs.append((a, b, w["maxspeed"], edit))
    out = signs.copy()
    dist, osm_ms, osm_dt, sign_dt, newer, verdict = [], [], [], [], [], []
    for r in signs.itertuples():
        p = tri.enu(r.lon, r.lat, lon0, lat0)
        best_d, best_ms, best_edit = math.inf, None, None
        for a, b, ms, edit in segs:
            d = _seg_dist_m(p, a, b)
            if d < best_d:
                best_d, best_ms, best_edit = d, ms, edit
        sign_ms = getattr(r, "obs_date_ms", None)
        sign_after = (sign_ms is not None and best_edit is not None
                      and sign_ms >= best_edit)
        sign_v, osm_v = _ms_int(r.value), _ms_int(best_ms)
        if best_d > max_road_m:
            v = "off_route"
        elif osm_v is None:
            v = "osm_missing"            # sign exists, OSM has no speed → enrich
        elif sign_v == osm_v:
            v = "agree"
        elif sign_after:
            v = "disagree_osm_stale"     # sign newer than OSM edit → fix OSM
        else:
            v = "disagree_check"         # OSM edited after the image → re-verify
        dist.append(best_d); osm_ms.append(best_ms)
        osm_dt.append(_day(best_edit)); sign_dt.append(_day(sign_ms))
        newer.append("sign" if sign_after else "osm")
        verdict.append(v)
    out["dist_road_m"] = dist
    out["osm_maxspeed"] = osm_ms
    out["osm_edit_date"] = osm_dt
    out["sign_obs_date"] = sign_dt
    out["sign_newer"] = newer
    out["verdict"] = verdict
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="QL.51")
    ap.add_argument("--bbox", default=DEFAULT_BBOX, help="S,W,N,E corridor search box")
    ap.add_argument("--limit-tiles", type=int, default=0)
    ap.add_argument("--since-months", type=int, default=24,
                    help="drop detections from images older than this (0 = keep all)")
    args = ap.parse_args()

    token = os.environ.get("MAPILLARY_TOKEN")
    if not token:
        print("set MAPILLARY_TOKEN (MLY|…)", file=sys.stderr)
        return 2

    ways = fetch_route_ways(args.ref, args.bbox)
    if not ways:
        print(f"no OSM ways found for ref {args.ref} in {args.bbox}", file=sys.stderr)
        return 1
    with_ms = sum(1 for w in ways if _ms_int(w["maxspeed"]) is not None)
    print(f"{args.ref}: {len(ways)} OSM ways · {with_ms} carry maxspeed "
          f"({100*with_ms/len(ways):.0f}%)")
    enrich_maxspeed_age(ways, DATA / f"{args.ref.replace('.', '_')}_msage.json")

    plan = corridor_tiles(ways, TILE_DEG)
    if args.limit_tiles:
        plan = plan[: args.limit_tiles]
    print(f"corridor → {len(plan)} tiles of {TILE_DEG}°; crawling Mapillary…")

    obs = pull_observations(plan, token)
    obs = filter_recent(obs, args.since_months)
    DATA.mkdir(exist_ok=True)
    obs.to_parquet(DATA / "ql51_observations.parquet", index=False)
    signs = triangulate_observations(obs)
    if not len(signs):
        print(f"{len(obs)} detections but no sign had ≥2 triangulable views")
        return 0

    lon0 = float(np.mean([lon for w in ways for lon, _ in w["line"]]))
    lat0 = float(np.mean([lat for w in ways for _, lat in w["line"]]))
    signs = compare(signs, ways, lon0, lat0)
    signs.to_parquet(DATA / "ql51_signs.parquet", index=False)

    e = signs["ref_err_m"]
    print(f"\ntriangulated {len(signs)} signs · err vs Mapillary ref: "
          f"median {e.median():.1f} m · p90 {e.quantile(0.9):.1f} m")
    print(f"mean views/sign {signs['n_views'].mean():.1f} · "
          f"median dist to OSM road {signs['dist_road_m'].median():.1f} m")
    vc = Counter(signs["verdict"])
    print("\nvs OSM maxspeed (verdict uses sign-date vs OSM-edit-date):")
    labels = {
        "agree": "agree (OSM confirmed)",
        "disagree_osm_stale": "disagree, sign newer → FIX OSM",
        "disagree_check": "disagree, OSM edited after image → re-verify",
        "osm_missing": "OSM has no maxspeed → enrich",
        "off_route": "off route (skip)",
    }
    for k, lab in labels.items():
        if vc.get(k):
            print(f"  {vc[k]:3d}  {lab}")
    actionable = signs[signs["verdict"].isin(["disagree_osm_stale", "disagree_check"])]
    if len(actionable):
        print("\ndisagreements (sign km/h vs OSM · dates):")
        for r in actionable.itertuples():
            tag = "OSM STALE" if r.verdict == "disagree_osm_stale" else "re-verify"
            print(f"  [{tag}] sign {r.value} vs osm {r.osm_maxspeed}  "
                  f"@ {r.lat:.5f},{r.lon:.5f}  "
                  f"sign seen {r.sign_obs_date}, osm edited {r.osm_edit_date}  "
                  f"({r.n_views} views, {r.dist_road_m:.0f} m off road)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
