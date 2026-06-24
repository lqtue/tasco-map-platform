"""Step 7 — aggregate Open Buildings centroids to res-11 H3 for POI-call sizing.

For each res-11 H3 cell with ≥1 building centroid, emits:
  [h3_11, h3_10, h3_9, province, n_buildings, built_area_m2]

Parent IDs are pre-computed so the dashboard rolls up to any resolution
without re-reading the 3.4 GB of building CSVs.

Province is joined from data/cells.parquet (res-10 parent → province).

Output: data/building_density.parquet  (gitignored like the rest of data/)
"""
import glob
from pathlib import Path

import duckdb
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
EXPECTED_BUILDINGS = 66_095_877  # total from cells.parquet; used for self-check


def main() -> None:
    csvs = sorted(glob.glob(str(DATA / "buildings" / "*.csv")))
    if not csvs:
        raise SystemExit("No building CSVs in data/buildings/ — run prep/02_gee_buildings.py first.")

    print(f"Aggregating {len(csvs)} province CSVs → res-11 …")
    con = duckdb.connect()
    con.execute("INSTALL h3 FROM community; LOAD h3;")

    density = con.execute(
        """
        WITH cells11 AS (
            SELECT
                h3_latlng_to_cell_string(lat, lon, 11) AS h3_11,
                area
            FROM read_csv_auto(?, union_by_name=true)
            WHERE lat IS NOT NULL AND lon IS NOT NULL
        )
        SELECT
            h3_11,
            h3_cell_to_parent(h3_11, 10)::VARCHAR AS h3_10,
            h3_cell_to_parent(h3_11, 9)::VARCHAR  AS h3_9,
            COUNT(*)  AS n_buildings,
            SUM(area) AS built_area_m2
        FROM cells11
        GROUP BY 1, 2, 3
        """,
        [csvs],
    ).df()

    print(f"  res-11 cells with buildings: {len(density):,}")

    # attach province via res-10 parent → cells.parquet
    cells = pd.read_parquet(DATA / "cells.parquet", columns=["h3_id", "province"])
    density = density.merge(cells, left_on="h3_10", right_on="h3_id", how="left").drop(columns=["h3_id"])

    out = DATA / "building_density.parquet"
    density.to_parquet(out, index=False)
    print(f"Wrote {out}")

    total = int(density.n_buildings.sum())
    print(f"Total buildings: {total:,}  (expected ~{EXPECTED_BUILDINGS:,})")
    assert abs(total - EXPECTED_BUILDINGS) < 1_000, \
        f"Building count mismatch: got {total}, expected {EXPECTED_BUILDINGS}"
    print("Self-check passed.")


if __name__ == "__main__":
    main()
