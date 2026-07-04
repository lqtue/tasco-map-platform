"""Triangulate a traffic sign's ground position from multiple street-view views.

The geometry core of the self-crawl sign pipeline (plan: design doc + prototype).
A detection in one image gives only a *bearing* from the camera to the sign; two
or more bearings to the same physical sign intersect at its position. We solve
that intersection as least-squares ray intersection in a local tangent plane,
robustified with RANSAC against bad detections / consumer-GPS noise, then merge
repeated detections of one sign with directional clustering.

Method follows the crowdsourced object-geolocation literature:
  Krylov, Kenny & Dahyot (2018) Remote Sensing 10(5):661  doi:10.3390/rs10050661
  Krylov & Dahyot (2019)  doi:10.1007/978-3-030-13453-2_7
  Pedersen & Torp (2021) directional clustering  (already in research/)

This module is network-free and provider-agnostic: it consumes plain
(camera lon/lat, bearing) rays, whichever source produced them (Mapillary now,
GSV / dashcam later). Run it directly to execute the synthetic self-check.
"""
from __future__ import annotations

import math
import random

import numpy as np
from sklearn.cluster import DBSCAN

R_EARTH = 6378137.0  # WGS84 equatorial radius (m)


# --- local tangent plane (equirectangular) ---------------------------------
# ponytail: equirectangular local plane — exact enough at meter level over a
# road bbox (<~50 km). Swap for a pyproj AEQD transformer if a region ever
# spans more than that.
def enu(lon, lat, lon0, lat0):
    """(lon,lat) deg -> (east,north) meters about the anchor (lon0,lat0)."""
    e = math.radians(lon - lon0) * math.cos(math.radians(lat0)) * R_EARTH
    n = math.radians(lat - lat0) * R_EARTH
    return np.array([e, n], dtype=float)


def enu_inv(e, n, lon0, lat0):
    """(east,north) meters -> (lon,lat) deg about the anchor."""
    lat = lat0 + math.degrees(n / R_EARTH)
    lon = lon0 + math.degrees(e / (R_EARTH * math.cos(math.radians(lat0))))
    return lon, lat


def bearing_dir(bearing_deg):
    """Compass bearing (0=N, 90=E, clockwise) -> unit (east,north) vector."""
    r = math.radians(bearing_deg)
    return np.array([math.sin(r), math.cos(r)], dtype=float)


def bearing_between(p_from, p_to):
    """Compass bearing (deg) from one ENU point to another."""
    de, dn = p_to[0] - p_from[0], p_to[1] - p_from[1]
    return math.degrees(math.atan2(de, dn)) % 360.0


# --- detection pixel -> bearing --------------------------------------------
def detection_bearing(compass_angle, x_px, width, camera_type, camera_params=None):
    """Bearing (deg) from a camera to a detection at horizontal pixel x_px.

    `camera_type` ∈ {perspective, fisheye, equirectangular/spherical}. For
    perspective Mapillary cameras `camera_params=[focal,k1,k2]` with focal
    normalised by max(width,height). Conventions (image-center = heading,
    +x = right) are the calibration knobs to verify against ground truth.
    """
    ct = (camera_type or "").lower()
    if ct in ("equirectangular", "spherical"):
        # full 360° pano: pixel column maps linearly to azimuth, center = heading
        return (compass_angle + (x_px / width - 0.5) * 360.0) % 360.0
    # perspective / fisheye: small-angle pinhole offset from the optical axis
    focal = (camera_params[0] if camera_params else 0.85) * max(width, 1)
    off = math.degrees(math.atan2((x_px - width / 2.0), focal))
    return (compass_angle + off) % 360.0


# --- core: least-squares ray intersection ----------------------------------
def _perp_dist(x, p, d):
    """Perpendicular distance from point x to the ray through p with unit dir d."""
    v = x - p
    return float(np.linalg.norm(v - np.dot(v, d) * d))


def _max_parallax(dirs):
    """Widest pairwise angle (deg) between ray directions — the geometry
    quality. One well-separated pair is enough to constrain the point; near 0
    means every ray is ~parallel, so the position is poorly determined."""
    angs = [math.degrees(math.atan2(d[0], d[1])) for d in dirs]
    best = 0.0
    for i in range(len(angs)):
        for j in range(i + 1, len(angs)):
            diff = abs(angs[i] - angs[j]) % 360.0
            diff = min(diff, 360.0 - diff)
            best = max(best, diff)
    return best


def triangulate(origins, dirs, min_parallax_deg=5.0):
    """Least-squares intersection of N rays (ENU meters).

    origins (N,2), dirs (N,2 unit). Returns (point(2,), rms_spread_m,
    parallax_deg) or None when the geometry is degenerate (parallel / too few).
    """
    origins = np.asarray(origins, float)
    dirs = np.asarray(dirs, float)
    if len(origins) < 2:
        return None
    parallax = _max_parallax(dirs)
    if parallax < min_parallax_deg:
        return None
    A = np.zeros((2, 2))
    b = np.zeros(2)
    for p, d in zip(origins, dirs):
        P = np.eye(2) - np.outer(d, d)  # projector onto the ray's normal
        A += P
        b += P @ p
    if np.linalg.cond(A) > 1e8:
        return None
    x = np.linalg.solve(A, b)
    spread = math.sqrt(np.mean([_perp_dist(x, p, d) ** 2 for p, d in zip(origins, dirs)]))
    return x, spread, parallax


def triangulate_ransac(origins, dirs, thresh_m=3.0, iters=80, min_parallax_deg=5.0, seed=0):
    """RANSAC ray intersection: rejects outlier detections / GPS spikes.

    Returns (point, rms_spread_m, parallax_deg, inlier_idx) or None.
    """
    origins = np.asarray(origins, float)
    dirs = np.asarray(dirs, float)
    n = len(origins)
    if n < 2:
        return None
    if n == 2:
        r = triangulate(origins, dirs, min_parallax_deg)
        return None if r is None else (*r, [0, 1])
    rng = random.Random(seed)
    best_inl: list[int] = []
    for _ in range(iters):
        i, j = rng.sample(range(n), 2)
        r = triangulate(origins[[i, j]], dirs[[i, j]], min_parallax_deg)
        if r is None:
            continue
        x = r[0]
        inl = [k for k in range(n) if _perp_dist(x, origins[k], dirs[k]) < thresh_m]
        if len(inl) > len(best_inl):
            best_inl = inl
    if len(best_inl) < 2:
        return None
    r = triangulate(origins[best_inl], dirs[best_inl], min_parallax_deg)
    return None if r is None else (*r, best_inl)


# --- dedup: directional clustering -----------------------------------------
def _ang_diff(a, b):
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def cluster_signs(points, values, headings=None, eps_m=8.0, head_deg=45.0):
    """Merge triangulated candidates of the same physical sign.

    Directional DBSCAN (Pedersen & Torp): two candidates join only if they are
    within eps_m, carry the same `value`, and (when headings given) face within
    head_deg — so the entering vs leaving sign of a speed zone stay distinct.
    Returns a cluster-label array (len == len(points)); -1 never occurs
    (min_samples=1, so singletons are their own cluster).
    """
    pts = np.asarray(points, float)
    n = len(pts)
    if n == 0:
        return np.array([], dtype=int)
    far = eps_m * 1e6  # sklearn's precomputed metric rejects inf; use a finite "unreachable"
    D = np.full((n, n), far)
    for i in range(n):
        for j in range(n):
            if values[i] != values[j]:
                continue
            if headings is not None and _ang_diff(headings[i], headings[j]) > head_deg:
                continue
            D[i, j] = np.linalg.norm(pts[i] - pts[j])
    return DBSCAN(eps=eps_m, min_samples=1, metric="precomputed").fit_predict(D)


# --- self-check ------------------------------------------------------------
def _demo():
    """ponytail self-check: recover a known sign from noisy rays; reject a
    degenerate (near-parallel) geometry; dedup duplicates into the right count."""
    rng = random.Random(42)

    # 1. recover a sign at (50, 80) m seen from 6 cameras driving along y≈0
    sign = np.array([50.0, 80.0])
    origins, dirs = [], []
    for x in (0, 12, 24, 36, 48, 60):
        cam = np.array([x + rng.gauss(0, 1.5), rng.gauss(0, 1.5)])  # ~1.5 m GPS noise
        true_b = bearing_between(cam, sign)
        d = bearing_dir(true_b + rng.gauss(0, 1.0))  # ~1° bearing noise
        origins.append(cam)
        dirs.append(d)
    # inject one gross outlier detection
    origins.append(np.array([30.0, 0.0]))
    dirs.append(bearing_dir(200.0))
    res = triangulate_ransac(origins, dirs, thresh_m=3.0)
    assert res is not None, "triangulation failed on a well-posed scene"
    x, spread, parallax, inl = res
    err = float(np.linalg.norm(x - sign))
    assert err < 5.0, f"recovered {x} err {err:.2f} m too high"
    assert len(inl) >= 6, f"RANSAC kept {len(inl)} inliers, dropped good rays"
    print(f"[1] recovered sign within {err:.2f} m  (spread {spread:.2f} m, "
          f"parallax {parallax:.1f}°, {len(inl)} inliers)")

    # 2. near-parallel rays (all cameras far away, almost same bearing) -> reject
    far_o = [np.array([x, -2000.0]) for x in (0, 5, 10)]
    far_d = [bearing_dir(bearing_between(o, sign)) for o in far_o]
    assert triangulate(far_o, far_d, min_parallax_deg=5.0) is None, "did not reject parallel rays"
    print("[2] rejected degenerate near-parallel geometry")

    # 3. dedup: two real 50-signs (8 m apart faces same way) + a 60-sign nearby
    pts = [[0, 0], [0.5, 0.3], [40, 0], [40.4, -0.2], [0.2, -0.4]]
    vals = ["50", "50", "50", "50", "60"]
    heads = [90, 90, 90, 90, 90]
    labels = cluster_signs(pts, vals, heads, eps_m=8.0)
    assert len(set(labels)) == 3, f"expected 3 signs, got {len(set(labels))}: {labels}"
    print(f"[3] deduped 5 detections -> {len(set(labels))} physical signs")

    print("self-check OK")


if __name__ == "__main__":
    _demo()
