"""Mapillary adapter for the sign-triangulation prototype (plan step 1).

Pulls Mapillary *per-image* speed-limit detections along a road bbox, converts
each to a bearing ray, triangulates per physical sign, and scores the recovered
position against Mapillary's own published map_feature position (a free
reference). This proves the triangulation geometry on real data; SAM3 later
*replaces* the detector step and emits the same observation rows.

Each map_feature (Mapillary's deduped sign) links several detections, each tied
to one image with a known pose (lng/lat + compass_angle + camera model) and a
pixel polygon (the sign's location in that image). pixel-x + pose -> bearing.

Provider-agnostic by construction: everything downstream consumes the
`sign_observations` row shape, so GSV / dashcam adapters can fill the same shape
later. Geometry lives in triangulate.py; this file is just the Mapillary I/O.

Usage:
  MAPILLARY_TOKEN=MLY|... python3 traffic/signs/detections_pull.py --bbox hanoi --limit-tiles 4
  python3 traffic/signs/detections_pull.py --selfcheck      # no network; tests the glue

Outputs (traffic/signs/data/):
  sign_observations.parquet   one row per per-image detection
  signs_triangulated.parquet  one row per deduped physical sign + error vs reference
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

import triangulate as tri
from mapillary_signs import BBOXES, OBJECT_VALUES, SPEED_RE, fetch, tiles

try:
    import mapbox_vector_tile
except ImportError:  # pragma: no cover - decode is optional until live pull
    mapbox_vector_tile = None

BASE = "https://graph.mapillary.com"
DATA = Path(__file__).resolve().parent / "data"
IMG_FIELDS = "id,geometry,computed_compass_angle,compass_angle,camera_type,camera_parameters,width,height,captured_at"


# --- Mapillary detection pixel geometry decode -----------------------------
def _flatten(coords):
    """Yield (x,y) pairs from arbitrarily nested GeoJSON-style coordinate lists."""
    if not coords:
        return
    if isinstance(coords[0], (int, float)):
        yield float(coords[0]), float(coords[1])
        return
    for c in coords:
        yield from _flatten(c)


def detection_xfrac(b64):
    """Decode a Mapillary detection's base64 vector-tile geometry to the sign's
    horizontal centroid as a fraction [0,1] of image width. None if undecodable."""
    if not b64 or mapbox_vector_tile is None:
        return None
    try:
        layers = mapbox_vector_tile.decode(base64.b64decode(b64))
    except Exception:
        return None
    xs = []
    for layer in layers.values():
        extent = layer.get("extent", 4096) or 4096
        for feat in layer.get("features", []):
            for x, _ in _flatten(feat.get("geometry", {}).get("coordinates", [])):
                xs.append(x / extent)
    return sum(xs) / len(xs) if xs else None


# --- Mapillary Graph API pulls ---------------------------------------------
def map_features_in_tile(tile, token):
    """Yield speed-limit map_features (deduped signs) in one bbox tile:
    {mf_id, value, ref_lng, ref_lat}. ref_* is Mapillary's published position."""
    w, s, e, n = tile
    url = f"{BASE}/map_features?fields=id,object_value,geometry&object_values={OBJECT_VALUES}&bbox={w},{s},{e},{n}"
    while url:
        payload = fetch(url, token)
        for f in payload.get("data", []):
            ov = f.get("object_value", "")
            coords = (f.get("geometry") or {}).get("coordinates")
            if not ov.startswith("regulatory--maximum-speed-limit") or not coords:
                continue
            m = SPEED_RE.search(ov)
            yield {
                "mf_id": f.get("id"),
                "value": int(m.group(1)) if m else None,
                "ref_lng": coords[0],
                "ref_lat": coords[1],
            }
        url = (payload.get("paging") or {}).get("next")


def detections_for_feature(mf_id, token):
    """Per-image detections of one map_feature: [{image_id, xfrac}]."""
    url = f"{BASE}/{mf_id}/detections?fields=id,value,image,geometry"
    out = []
    while url:
        payload = fetch(url, token)
        for d in payload.get("data", []):
            img = (d.get("image") or {}).get("id")
            xf = detection_xfrac(d.get("geometry"))
            if img and xf is not None:
                out.append({"image_id": img, "xfrac": xf})
        url = (payload.get("paging") or {}).get("next")
    return out


def image_meta(image_id, token, cache):
    """Pose + camera model for an image (cached — many detections share images)."""
    if image_id in cache:
        return cache[image_id]
    payload = fetch(f"{BASE}/{image_id}?fields={IMG_FIELDS}", token)
    coords = (payload.get("geometry") or {}).get("coordinates") or [None, None]
    meta = {
        "lng": coords[0],
        "lat": coords[1],
        "compass": payload.get("computed_compass_angle", payload.get("compass_angle")),
        "camera_type": payload.get("camera_type"),
        "camera_params": payload.get("camera_parameters"),
        "width": payload.get("width") or 1,
        "height": payload.get("height") or 1,
        "captured_at": payload.get("captured_at"),
    }
    cache[image_id] = meta
    return meta


def pull_observations(plan, token):
    """Walk tiles -> map_features -> detections -> image poses; one row per
    detection with the bearing already computed. Returns a DataFrame."""
    rows, img_cache = [], {}
    for i, t in enumerate(plan, 1):
        for mf in map_features_in_tile(t, token):
            for det in detections_for_feature(mf["mf_id"], token):
                m = image_meta(det["image_id"], token, img_cache)
                if m["lng"] is None or m["compass"] is None:
                    continue
                x_px = det["xfrac"] * m["width"]
                bearing = tri.detection_bearing(
                    m["compass"], x_px, m["width"], m["camera_type"], m["camera_params"]
                )
                rows.append({
                    "image_id": det["image_id"],
                    "lon": m["lng"], "lat": m["lat"],
                    "compass_angle": m["compass"], "camera_type": m["camera_type"],
                    "bearing_deg": bearing,
                    "attr": "maxspeed", "value": str(mf["value"]),
                    "source": "mapillary", "observed_at": m["captured_at"],
                    "image_ref": f"https://www.mapillary.com/app/?image_key={det['image_id']}",
                    "map_feature_id": mf["mf_id"],
                    "ref_lon": mf["ref_lng"], "ref_lat": mf["ref_lat"],
                })
        print(f"  {i}/{len(plan)} tiles · {len(rows)} detections", flush=True)
    return pd.DataFrame(rows)


def filter_recent(obs, since_months):
    """Drop detections from images older than `since_months` (Mapillary
    `captured_at` is epoch ms). 0 = keep all. Keeps the triangulated position
    reflecting the sign's *current* state, not a years-old drive-by."""
    if not since_months or not len(obs):
        return obs
    cutoff_ms = (time.time() - since_months * 30.44 * 86400) * 1000.0
    at = pd.to_numeric(obs["observed_at"], errors="coerce")
    keep = obs[at >= cutoff_ms]
    print(f"  freshness (≤ {since_months} mo): {len(obs)} → {len(keep)} detections")
    return keep


# --- triangulate grouped observations --------------------------------------
def triangulate_observations(obs):
    """Group observations by map_feature, triangulate each, score vs reference.
    Returns the triangulated-signs DataFrame."""
    out = []
    for mf_id, g in obs.groupby("map_feature_id"):
        if len(g) < 2:
            continue
        lon0, lat0 = float(g["lon"].mean()), float(g["lat"].mean())
        origins = [tri.enu(r.lon, r.lat, lon0, lat0) for r in g.itertuples()]
        dirs = [tri.bearing_dir(r.bearing_deg) for r in g.itertuples()]
        res = tri.triangulate_ransac(origins, dirs)
        if res is None:
            continue
        x, spread, parallax, inl = res
        lon, lat = tri.enu_inv(x[0], x[1], lon0, lat0)
        ref = tri.enu(float(g["ref_lon"].iloc[0]), float(g["ref_lat"].iloc[0]), lon0, lat0)
        err_m = float(np.linalg.norm(x - ref))
        # newest image that saw this sign — the evidence's freshness, to compare
        # against the OSM segment's last-edit time downstream
        obs_date_ms = pd.to_numeric(g["observed_at"], errors="coerce").max()
        out.append({
            "lon": lon, "lat": lat, "value": g["value"].iloc[0], "attr": "maxspeed",
            "n_views": len(inl), "ray_spread_m": spread, "parallax_deg": parallax,
            "source": "mapillary", "map_feature_id": mf_id,
            "ref_err_m": err_m,
            "obs_date_ms": float(obs_date_ms) if pd.notna(obs_date_ms) else None,
            "member_image_ids": list(g["image_id"]),
        })
    return pd.DataFrame(out)


def _report(signs):
    if not len(signs):
        print("no signs triangulated (need ≥2 decodable views per sign)")
        return
    e = signs["ref_err_m"]
    print(f"triangulated {len(signs)} signs · error vs Mapillary ref: "
          f"median {e.median():.1f} m · p90 {e.quantile(0.9):.1f} m · max {e.max():.1f} m")
    print(f"  mean views/sign {signs['n_views'].mean():.1f} · "
          f"median ray spread {signs['ray_spread_m'].median():.2f} m")


# --- self-check (no network) -----------------------------------------------
def _selfcheck():
    """Build two synthetic views of a sign as observation rows, run the real
    grouping+triangulation+scoring path, assert the recovered point is close to
    a reference placed at truth. Exercises the glue triangulate.py doesn't."""
    truth_lon, truth_lat = 105.8000, 21.0050
    cams = [(105.79990, 21.00480), (105.80030, 21.00470)]
    rows = []
    for lon, lat in cams:
        bearing = tri.bearing_between(
            tri.enu(lon, lat, truth_lon, truth_lat),
            np.array([0.0, 0.0]),  # truth at the ENU origin
        )
        rows.append({
            "image_id": f"img{lon}", "lon": lon, "lat": lat,
            "compass_angle": bearing, "camera_type": "perspective",
            "bearing_deg": bearing, "attr": "maxspeed", "value": "60",
            "source": "mapillary", "observed_at": 0, "image_ref": "",
            "map_feature_id": "mf1", "ref_lon": truth_lon, "ref_lat": truth_lat,
        })
    signs = triangulate_observations(pd.DataFrame(rows))
    assert len(signs) == 1, f"expected 1 sign, got {len(signs)}"
    assert signs["ref_err_m"].iloc[0] < 2.0, f"err {signs['ref_err_m'].iloc[0]:.2f} m too high"
    print(f"selfcheck OK · recovered within {signs['ref_err_m'].iloc[0]:.2f} m of reference")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", default="hanoi", help="preset or minlon,minlat,maxlon,maxlat")
    ap.add_argument("--tile-deg", type=float, default=0.02)
    ap.add_argument("--limit-tiles", type=int, default=0, help="stop after N tiles (testing)")
    ap.add_argument("--since-months", type=int, default=0,
                    help="drop detections from images older than this (0 = keep all)")
    ap.add_argument("--selfcheck", action="store_true", help="run the no-network glue test")
    args = ap.parse_args()

    if args.selfcheck:
        _selfcheck()
        return 0

    bbox = BBOXES.get(args.bbox)
    if bbox is None:
        bbox = tuple(float(v) for v in args.bbox.split(","))
    plan = list(tiles(bbox, args.tile_deg))
    if args.limit_tiles:
        plan = plan[: args.limit_tiles]
    print(f"bbox {bbox} → {len(plan)} tiles")

    token = os.environ.get("MAPILLARY_TOKEN")
    if not token:
        print("set MAPILLARY_TOKEN (MLY|…) — free at mapillary.com/dashboard/developers", file=sys.stderr)
        return 2
    if mapbox_vector_tile is None:
        print("pip install mapbox-vector-tile (needed to decode detection geometry)", file=sys.stderr)
        return 2

    obs = pull_observations(plan, token)
    obs = filter_recent(obs, args.since_months)
    DATA.mkdir(exist_ok=True)
    obs.to_parquet(DATA / "sign_observations.parquet", index=False)
    print(f"wrote sign_observations.parquet: {len(obs)} detections")

    signs = triangulate_observations(obs)
    signs.to_parquet(DATA / "signs_triangulated.parquet", index=False)
    _report(signs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
