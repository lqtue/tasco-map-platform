"""Step 1 — Admin + islands.

Reads the 2025 Vietnam ward boundary (single authoritative layer, EPSG:4326) and
writes a clean GeoParquet keyed for downstream cell->admin joins and island polyfill.

  province = tentinh   ward = tenhc   island = (loai == "đặc khu")
"""
import sys
from pathlib import Path
import geopandas as gpd

SRC = Path("/Users/airm1/Downloads/VietnamWardBoundary2025.geojson")
OUT = Path(__file__).resolve().parents[1] / "data" / "admin_wards.parquet"
ISLAND_TYPE = "đặc khu"


def main() -> None:
    g = gpd.read_file(SRC)
    if g.crs is None or g.crs.to_epsg() != 4326:
        g = g.to_crs(4326)

    g = g.rename(columns={"tentinh": "province", "tenhc": "ward"})
    g["is_island"] = g["loai"] == ISLAND_TYPE
    g = g[["ma", "province", "ward", "loai", "is_island", "geometry"]]

    n_prov = g["province"].nunique()
    n_isl = int(g["is_island"].sum())
    assert n_prov == 34, f"expected 34 provinces, got {n_prov}"
    assert n_isl == 13, f"expected 13 đặc khu islands, got {n_isl}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    g.to_parquet(OUT)
    print(f"wrote {OUT}  ({len(g)} wards, {n_prov} provinces, {n_isl} island zones)")
    print("islands:", ", ".join(sorted(g.loc[g.is_island, "ward"])))


if __name__ == "__main__":
    sys.exit(main())
