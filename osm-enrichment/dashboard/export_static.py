"""Precompute a compact data bundle for the static HTML dashboard.

The Streamlit app recomputes over ~5M res-10 H3 cells on every interaction. For a
board demo we instead bake the answers once: a coarse **res-7** hex grid for the
map (~tens of thousands of cells, not millions) and **per-province** threshold /
gap aggregates the browser can sum instantly. The HTML then needs no server and
ships a few MB instead of hundreds.

Reads the same sources as the dashboard (cells.parquet + road_coverage_cells.parquet
+ baseline JSONs) and writes  osm-enrichment/dashboard/static/data.js  as
`window.DATA = {...}` (a .js, not .json, so index.html can load it via file://).

Run:  coverage/.venv/bin/python osm-enrichment/dashboard/export_static.py
"""
import json
from pathlib import Path

import h3
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
COVERAGE_DATA = REPO / "coverage/data"
BASELINE = REPO / "osm-enrichment/baseline"
OUT = Path(__file__).resolve().parent / "static/data.js"

THRESHOLDS = [0.0, 0.05, 0.10, 0.20, 0.30]
MAP_RES = 7  # ~5 km²/cell — coarse enough for a snappy national overview


def load_cells():
    """Same union as the dashboard's load_cells (res-10 master + road sidecar)."""
    base = pd.read_parquet(COVERAGE_DATA / "cells.parquet")
    rc = pd.read_parquet(COVERAGE_DATA / "road_coverage_cells.parquet")
    metric = ["road_km", "maxspeed_km", "name_km", "lanes_km", "top_class"]
    new = rc[~rc["h3_id"].isin(base["h3_id"])].copy()
    new["built_up_area_m2"] = 0.0
    new["building_count"] = 0
    for f in ("road_built", "road_construction", "is_island", "is_island_land"):
        new[f] = False
    new["road_built_class"] = None
    new["road_constr_class"] = None
    new["built_up_ratio"] = 0.0
    new = new.reindex(columns=base.columns)
    base = pd.concat([base, new], ignore_index=True)
    base = base.merge(rc[["h3_id"] + metric], on="h3_id", how="left")
    for c in ("road_km", "maxspeed_km", "name_km"):
        base[c] = base[c].fillna(0.0)
    base["maxspeed_gap_km"] = (base["road_km"] - base["maxspeed_km"]).clip(lower=0)
    base["name_gap_km"] = (base["road_km"] - base["name_km"]).clip(lower=0)
    base["prov"] = base["province"].fillna("(không rõ)")
    return base


def province_table(base, provinces):
    """Per-province gap km + buy/urban km² at each built-up threshold."""
    idx = {p: i for i, p in enumerate(provinces)}
    rows = [{"ms_gap": 0.0, "name_gap": 0.0, "road_km": 0.0, "island_km2": 0.0,
             "buy_km2": [0.0] * len(THRESHOLDS), "urban_km2": [0.0] * len(THRESHOLDS)}
            for _ in provinces]

    g = base.groupby("prov")
    for p, v in (g["maxspeed_gap_km"].sum()).items():
        rows[idx[p]]["ms_gap"] = round(float(v), 1)
    for p, v in (g["name_gap_km"].sum()).items():
        rows[idx[p]]["name_gap"] = round(float(v), 1)
    for p, v in (g["road_km"].sum()).items():
        rows[idx[p]]["road_km"] = round(float(v), 1)
    isl = (base.assign(a=base["cell_area_m2"] * base["is_island_land"])
           .groupby("prov")["a"].sum() / 1e6)
    for p, v in isl.items():
        rows[idx[p]]["island_km2"] = round(float(v), 1)

    for ti, thr in enumerate(THRESHOLDS):
        urban = base["built_up_ratio"] >= thr
        buy = urban | base["road_built"] | base["road_construction"] | base["is_island_land"]
        bu = (base.assign(a=base["cell_area_m2"] * buy).groupby("prov")["a"].sum() / 1e6)
        uu = (base.assign(a=base["cell_area_m2"] * urban).groupby("prov")["a"].sum() / 1e6)
        for p, v in bu.items():
            rows[idx[p]]["buy_km2"][ti] = round(float(v), 1)
        for p, v in uu.items():
            rows[idx[p]]["urban_km2"][ti] = round(float(v), 1)
    return rows


def hexes(base, provinces):
    """Aggregate res-10 cells up to res-7 and emit a GeoJSON FeatureCollection.

    Polygons (not just H3 ids) so the page can render natively in MapLibre with
    no deck.gl/h3-js dependency. Coords rounded to 4 dp (~11 m, fine at res-7).
    """
    idx = {p: i for i, p in enumerate(provinces)}
    uniq9 = base["res9_id"].dropna().unique()
    to7 = {u: h3.cell_to_parent(u, MAP_RES) for u in uniq9}
    base = base.assign(res7=base["res9_id"].map(to7))
    base = base[base["res7"].notna()]

    agg = base.groupby("res7").agg(
        builtA=("built_up_area_m2", "sum"),
        cellA=("cell_area_m2", "sum"),
        road=("road_km", "sum"),
        ms=("maxspeed_gap_km", "sum"),
        nm=("name_gap_km", "sum"),
    )
    prov7 = base.groupby("res7")["prov"].agg(lambda s: s.value_counts().index[0])
    agg["prov"] = prov7
    agg["builtup"] = (agg["builtA"] / agg["cellA"]).clip(upper=1.0)

    feats = []
    for h, r in agg.iterrows():
        ring = [[round(lng, 4), round(lat, 4)] for lat, lng in h3.cell_to_boundary(h)]
        ring.append(ring[0])
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "b": round(float(r["builtup"]), 3),
                "m": round(float(r["ms"]), 1),
                "n": round(float(r["nm"]), 1),
                "r": round(float(r["road"]), 1),
                "p": int(idx[r["prov"]]),
            },
        })
    return {"type": "FeatureCollection", "features": feats}


def main():
    base = load_cells()
    provinces = sorted(base["prov"].unique())

    ms = json.loads((BASELINE / "maxspeed_coverage_result.json").read_text())
    nm = json.loads((BASELINE / "name_coverage_result.json").read_text())
    full = json.loads((BASELINE / "name_coverage_full_result.json").read_text())

    bundle = {
        "generated": "2026-06-10",
        "map_res": MAP_RES,
        "thresholds": THRESHOLDS,
        "provinces": provinces,
        "prov": province_table(base, provinces),
        "fc": hexes(base, provinces),
        "totals": {
            "network_km": round(ms["tertiary_plus"]["total_km"]),
            "ms_missing_km": round(ms["tertiary_plus"]["total_km"] - ms["tertiary_plus"]["maxspeed_km"]),
            "name_total_km": round(nm["total_km"]),
            "name_no_name_km": round(nm["no_name_km"]),
            "name_no_name_full_km": round(full["no_name_km"]),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.DATA = " + json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + ";\n")
    mb = OUT.stat().st_size / 1e6
    print(f"wrote {OUT.relative_to(REPO)}: {len(bundle['fc']['features']):,} hexes, "
          f"{len(provinces)} provinces, {mb:.1f} MB")


if __name__ == "__main__":
    main()
