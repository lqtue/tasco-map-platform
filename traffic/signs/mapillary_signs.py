"""Step 6 — Mapillary speed-limit traffic signs -> point parquet (street-view signal).

Pulls already-detected traffic signs from Mapillary's free **Map Features** Graph
API over a bbox, keeps the speed-limit family (`regulatory--maximum-speed-limit-*`),
parses the km/h value from the sign class, and writes one row per detected sign.

Why points, not a pre-binned hex layer: signs are sparse (tens of thousands
nationwide), so the dashboard bins them to its display H3 resolution at load —
that keeps the sign grid automatically consistent with the dashboard's
DISPLAY_RES (no resolution baked in here).

Mapillary's published detector is European-trained, so VN coverage/accuracy is
partial — this is the "phase 1" feed; a VN-specific retrain is a later track.

Auth: a Mapillary client token in env MAPILLARY_TOKEN (starts with "MLY|...").
Get one free at mapillary.com → developer → register an app.

Usage:
  MAPILLARY_TOKEN=MLY|... python prep/06_mapillary_signs.py --bbox hanoi
  MAPILLARY_TOKEN=MLY|... python prep/06_mapillary_signs.py            # all Vietnam
  python prep/06_mapillary_signs.py --bbox hanoi --dry-run            # print tile plan, no network

Output: data/mapillary_sign_points.parquet
        [lat, lng, value, object_value, sign_id, first_seen, last_seen]
"""
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "archive" / "admin-poi" / "coverage" / "data"
ROADS_PARQUET = DATA / "road_coverage_cells.parquet"  # tertiary+ cells, for the road pre-filter
API = "https://graph.mapillary.com/map_features"
FIELDS = "id,object_value,geometry,first_seen_at,last_seen_at"
SPEED_RE = re.compile(r"maximum-speed-limit-(\d+)")

# Server-side filter: fetch ONLY speed-limit signs, not every map feature. Two
# hard API limits force the shape here: (1) the per-request bbox must be tiny
# (dense tiles 500 even under the 0.01 sq-deg area cap), and (2) a very long
# object_values list also 500s — so keep the list lean. Mapillary's speed-limit
# class is `regulatory--maximum-speed-limit-{N}--g1` (the **g1** board style;
# g2/g3 don't occur in VN data). Full posted range 5–120.
SPEEDS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 120]
OBJECT_VALUES = ",".join(f"regulatory--maximum-speed-limit-{s}--g1" for s in SPEEDS)

# Map Features bbox must be small; tile the area into sub-bboxes of TILE_DEG.
TILE_DEG = 0.02  # ~2.2 km — dense urban tiles 500 above this

# named bbox presets (minlon, minlat, maxlon, maxlat)
BBOXES = {
    "vietnam": (102.10, 8.18, 109.55, 23.40),
    "hanoi": (105.70, 20.90, 106.00, 21.10),
    "hcmc": (106.55, 10.68, 106.85, 10.90),
    "danang": (108.10, 15.95, 108.30, 16.12),
}


def frange(lo, hi, step):
    x = lo
    while x < hi:
        yield x
        x += step


def tiles(bbox, step):
    w, s, e, n = bbox
    for x in frange(w, e, step):
        for y in frange(s, n, step):
            yield (x, y, min(x + step, e), min(y + step, n))


def tile_key(lon, lat, step):
    """Integer (col, row) of the tile a point falls in — matches tiles()' grid."""
    import math
    return (math.floor(lon / step), math.floor(lat / step))


def road_tile_keys(step):
    """Set of tile keys that contain a tertiary+ road, from the coverage road
    cells. Querying only these skips the ~86% of VN's bbox that is sea/mountain/
    field with no road — the cheap way to not overcrowd the API."""
    import numpy as np
    df = pd.read_parquet(ROADS_PARQUET, columns=["lat", "lng"])
    cols = np.floor(df["lng"].to_numpy() / step).astype(int)
    rows = np.floor(df["lat"].to_numpy() / step).astype(int)
    return set(zip(cols.tolist(), rows.tolist()))


def fetch(url, token, retries=7):
    """GET a Mapillary Graph API URL, return parsed JSON. Mapillary's
    map_features endpoint throws intermittent 500s, so retry generously with
    exponential backoff + jitter."""
    sep = "&" if "?" in url else "?"
    full = f"{url}{sep}access_token={token}" if "access_token=" not in url else url
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(full, timeout=60) as r:
                return json.loads(r.read())
        except OSError as ex:   # HTTPError, URLError, TimeoutError, socket errors
            code = getattr(ex, "code", None)
            transient = code in (429, 500, 502, 503) or not isinstance(ex, urllib.error.HTTPError)
            if transient and attempt < retries - 1:
                time.sleep(min(2 ** attempt, 20) + random.random())
                continue
            raise


def speed_signs_in_tile(tile, token):
    """Yield speed-limit sign rows in one bbox tile, following paging."""
    w, s, e, n = tile
    url = (f"{API}?fields={FIELDS}&object_values={OBJECT_VALUES}&bbox={w},{s},{e},{n}")
    while url:
        payload = fetch(url, token)
        for f in payload.get("data", []):
            ov = f.get("object_value", "")
            if not ov.startswith("regulatory--maximum-speed-limit"):
                continue
            geom = f.get("geometry") or {}
            coords = geom.get("coordinates")
            if not coords:
                continue
            m = SPEED_RE.search(ov)
            yield {
                "lat": coords[1], "lng": coords[0],
                "value": int(m.group(1)) if m else None,
                "object_value": ov,
                "sign_id": f.get("id"),
                "first_seen": f.get("first_seen_at"),
                "last_seen": f.get("last_seen_at"),
            }
        url = (payload.get("paging") or {}).get("next")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", default="vietnam",
                    help="preset name (vietnam/hanoi/hcmc/danang) or minlon,minlat,maxlon,maxlat")
    ap.add_argument("--tile-deg", type=float, default=TILE_DEG)
    ap.add_argument("--limit-tiles", type=int, default=0, help="stop after N tiles (testing)")
    ap.add_argument("--no-road-filter", action="store_true",
                    help="query every tile in the bbox, not just road-bearing ones")
    ap.add_argument("--since-months", type=int, default=36,
                    help="drop signs whose last_seen is older than this (0 = keep all-time)")
    ap.add_argument("--dry-run", action="store_true", help="print the tile plan, no network")
    args = ap.parse_args()

    if args.bbox in BBOXES:
        bbox = BBOXES[args.bbox]
    else:
        bbox = tuple(float(v) for v in args.bbox.split(","))
        if len(bbox) != 4:
            print("--bbox must be a preset or minlon,minlat,maxlon,maxlat", file=sys.stderr)
            return 2

    plan = list(tiles(bbox, args.tile_deg))
    # Pre-filter to tiles that actually contain a tertiary+ road (skip empty sea/
    # mountain tiles) — the main API-load reducer.
    if not args.no_road_filter and ROADS_PARQUET.exists():
        keep = road_tile_keys(args.tile_deg)
        before = len(plan)
        plan = [t for t in plan if tile_key(t[0], t[1], args.tile_deg) in keep]
        print(f"road pre-filter: {before:,} → {len(plan):,} tiles ({100*(1-len(plan)/before):.0f}% skipped)")
    elif not args.no_road_filter:
        print(f"(no {ROADS_PARQUET.name} — road pre-filter off)", file=sys.stderr)
    if args.limit_tiles:
        plan = plan[:args.limit_tiles]
    print(f"bbox {bbox} → {len(plan):,} tiles of {args.tile_deg}°")
    if args.dry_run:
        for t in plan[:5]:
            print("  tile", t)
        print("  …" if len(plan) > 5 else "")
        return 0

    token = os.environ.get("MAPILLARY_TOKEN")
    if not token:
        print("set MAPILLARY_TOKEN (MLY|...) — get one free at mapillary.com/dashboard/developers",
              file=sys.stderr)
        return 2

    rows, seen, failed = [], set(), 0
    for i, t in enumerate(plan, 1):
        try:
            for row in speed_signs_in_tile(t, token):
                if row["sign_id"] in seen:   # tiles share edges; dedup by sign id
                    continue
                seen.add(row["sign_id"])
                rows.append(row)
        except OSError:
            failed += 1   # flaky API (incl. timeouts) — skip this tile, don't kill the run
        time.sleep(0.15)  # be gentle on the API
        if i % 50 == 0 or i == len(plan):
            print(f"  {i:,}/{len(plan):,} tiles · {len(rows):,} signs · {failed} tile(s) skipped",
                  flush=True)

    out = pd.DataFrame(rows)
    # Freshness: Mapillary returns the all-time aggregate (no server-side date
    # filter exists on map_features), so drop stale signs by last_seen here —
    # an old last_seen means the sign hasn't been re-observed and may be gone.
    if args.since_months and len(out):
        cutoff = (pd.Timestamp.now(tz="UTC")
                  - pd.DateOffset(months=args.since_months))
        ls = pd.to_datetime(out["last_seen"], utc=True, errors="coerce")
        fresh = out[ls >= cutoff]
        print(f"freshness (last_seen ≥ {cutoff.date()}): {len(out):,} → {len(fresh):,} signs")
        out = fresh
    DATA.mkdir(exist_ok=True)
    out.to_parquet(DATA / "mapillary_sign_points.parquet", index=False)
    print(f"wrote mapillary_sign_points.parquet: {len(out):,} speed-limit signs")
    if len(out):
        vc = out["value"].value_counts(dropna=False).head(10).to_dict()
        print(f"  speed values (top): {vc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
