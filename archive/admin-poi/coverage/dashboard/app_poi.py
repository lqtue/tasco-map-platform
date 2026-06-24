"""POI call-volume sizing dashboard.

Goal: find the H3 resolution grid that covers every building in the Open Buildings
dataset with one AWS reverse-geocode call, without truncating results.

AWS SearchPlaceIndexForPosition returns max 50 results per call (1 cell = 1 call =
$0.50/1k). If a cell has >50 buildings the call is TRUNCATED — buildings are missed.
So the adaptive algorithm finds the coarsest resolution where buildings/cell ≤ 50.

  res-9  edge ~174 m  area ~0.105 km²   (too coarse for dense areas)
  res-10 edge ~66 m   area ~0.015 km²
  res-11 edge ~25 m   area ~0.002 km²   (finest; rarely truncates)

Data:  data/building_density.parquet  (run prep/07_building_density.py first)
Run:   streamlit run admin-poi/coverage/dashboard/app_poi.py
"""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "data"

AWS_RESULT_CAP = 50          # hard AWS limit — cells above this WILL truncate
COST_PER_1K = 0.50           # $0.50/1k calls — verify on AWS console before bulk run
DEFAULT_PROVS = ["Thủ đô Hà Nội", "thành phố Hồ Chí Minh"]


@st.cache_data
def load() -> pd.DataFrame:
    return pd.read_parquet(DATA / "building_density.parquet")


def res_summary(df: pd.DataFrame, cost_per_1k: float) -> pd.DataFrame:
    """Uniform-resolution comparison: truncation risk + cost at each resolution."""
    rows = []
    for res, col, edge_m in [(9, "h3_9", 174), (10, "h3_10", 66), (11, "h3_11", 25)]:
        grp = df.groupby(col)["n_buildings"].sum()
        calls = int((grp > 0).sum())
        avg_b = round(grp[grp > 0].mean(), 1) if calls else 0
        pct_trunc = round(100 * (grp > AWS_RESULT_CAP).sum() / max(calls, 1), 1)
        rows.append({
            "Resolution": f"res-{res}  (~{edge_m}m edge)",
            "Calls": calls,
            "Avg bldg/call": avg_b,
            "Cells > 50 bldg (truncated %)": f"{int((grp > AWS_RESULT_CAP).sum()):,}  ({pct_trunc}%)",
            "Est. cost ($)": f"${calls / 1000 * cost_per_1k:,.2f}" if cost_per_1k else "—",
        })
    return pd.DataFrame(rows)


def adaptive_calls(df: pd.DataFrame, cap: int) -> tuple[int, int, int, int]:
    """Coarsest resolution per area that keeps buildings/cell ≤ cap (no truncation).
    Greedy top-down: res-9 first, drill to res-10 then res-11 where density exceeds cap."""
    r9 = df.groupby("h3_9")["n_buildings"].sum()
    r9_ok = set(r9[r9 <= cap].index)

    rem = df[~df["h3_9"].isin(r9_ok)]
    r10 = rem.groupby("h3_10")["n_buildings"].sum()
    r10_ok = set(r10[r10 <= cap].index)

    # res-11 floor: cells still > cap accepted as irreducible (mall/market)
    rem2 = rem[~rem["h3_10"].isin(r10_ok)]
    r11_trunc = int((rem2["n_buildings"] > cap).sum())  # still truncated at floor
    r11 = int((rem2["n_buildings"] > 0).sum())

    total = len(r9_ok) + len(r10_ok) + r11
    return len(r9_ok), len(r10_ok), r11, total, r11_trunc


def main() -> None:
    st.set_page_config("POI Call Sizing", layout="wide")
    st.title("AWS Reverse-Geocode Crawl — H3 Resolution Sizing")
    st.caption(
        "Each H3 cell = 1 AWS `SearchPlaceIndexForPosition` call = **max 50 results**. "
        "If a cell has >50 buildings the call is **truncated** — buildings are missed. "
        "The adaptive plan finds the coarsest resolution that avoids truncation, minimising cost."
    )

    if not (DATA / "building_density.parquet").exists():
        st.error("data/building_density.parquet not found — run prep/07_building_density.py first.")
        return

    df = load()

    sb = st.sidebar
    sb.header("Scope")
    provs = sorted(df["province"].dropna().unique())
    sel_provs = sb.multiselect("Provinces (empty = all VN)", provs, DEFAULT_PROVS)

    sb.header("Truncation threshold")
    cap = sb.slider(
        "Max buildings / cell before subdividing",
        1, AWS_RESULT_CAP, AWS_RESULT_CAP,
        help=f"AWS hard cap = {AWS_RESULT_CAP} results. Cells above this threshold "
             "will have results truncated. Lower the slider to be conservative."
    )

    sb.header("Cost")
    cost_per_1k = sb.number_input(
        "$/1,000 calls  (verify on AWS console — $0.50 assumed)",
        min_value=0.0, step=0.05, value=COST_PER_1K, format="%.2f"
    )
    sb.caption("⚠️ $0.50/1k is an assumption. Confirm the actual rate on the AWS account "
               "or GrabMaps agreement before a bulk run.")

    view = df[df["province"].isin(sel_provs)] if sel_provs else df

    total_b = int(view["n_buildings"].sum())
    r11_calls = int((view["n_buildings"] > 0).sum())
    r11_trunc_uniform = int((view.groupby("h3_11")["n_buildings"].sum() > cap).sum())

    # ---- headline ----
    c1, c2, c3 = st.columns(3)
    c1.metric("Total buildings (Open Buildings)", f"{total_b:,}")
    c2.metric("Uniform res-11 calls", f"{r11_calls:,}",
              help="Finest resolution — minimal truncation risk, maximum cost.")
    c3.metric("Est. cost @ res-11", f"${r11_calls / 1000 * cost_per_1k:,.2f}")

    if r11_trunc_uniform:
        st.warning(f"Even at res-11: **{r11_trunc_uniform:,} cells still exceed {cap} buildings** "
                   "(irreducible — e.g. shopping malls). Results will be partially truncated there.")

    st.divider()

    # ---- resolution comparison ----
    st.subheader("Uniform-resolution comparison")
    st.caption("Pick one resolution for the whole area. Truncated % = cells where AWS will miss buildings.")
    st.dataframe(res_summary(view, cost_per_1k), hide_index=True, use_container_width=True)

    st.divider()

    # ---- adaptive plan ----
    st.subheader(f"Adaptive plan  (subdivide where buildings/cell > {cap})")
    st.caption(
        "Use res-9 for sparse areas, drill to res-10 / res-11 only where density demands it. "
        "Greedy top-down. Cells still above cap at res-11 floor are accepted as irreducible."
    )

    r9, r10, r11, total, r11_trunc = adaptive_calls(view, cap)
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("res-9 cells  (~174m)", f"{r9:,}")
    a2.metric("res-10 cells  (~66m)", f"{r10:,}")
    a3.metric("res-11 cells  (~25m)", f"{r11:,}")
    a4.metric("Total calls (adaptive)", f"{total:,}",
              delta=f"{total - r11_calls:+,} vs uniform res-11",
              delta_color="inverse")

    b1, b2 = st.columns(2)
    b1.metric("Est. cost (adaptive)", f"${total / 1000 * cost_per_1k:,.2f}")
    b2.metric("Residual truncated cells (res-11 floor)", f"{r11_trunc:,}",
              help="Cells still > cap at the finest resolution — irreducible dense spots.")

    st.divider()

    # ---- by-province ----
    st.subheader("By province (res-11 baseline)")
    by_prov = (
        view.groupby("province")
        .agg(buildings=("n_buildings", "sum"), calls_res11=("h3_11", "count"))
        .sort_values("calls_res11", ascending=False)
        .assign(est_cost_res11=lambda d: (d["calls_res11"] / 1000 * cost_per_1k).round(2))
        .reset_index()
    )
    st.dataframe(by_prov, hide_index=True, use_container_width=True)

    csv = by_prov.to_csv(index=False).encode()
    st.download_button("Download CSV", csv, "poi_call_sizing.csv", "text/csv")


if __name__ == "__main__":
    main()
