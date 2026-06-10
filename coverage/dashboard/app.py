"""Vietnam satellite-imagery coverage dashboard.

Live criteria -> selected res-10 H3 cells -> total km² + estimated cost, with a
pydeck hexagon map. Run:  streamlit run coverage/dashboard/app.py
"""
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "data"
ROAD_CLASSES = ["motorway", "trunk", "primary"]
MAX_RENDER = 250_000  # cap hexes sent to the browser

# category colors (RGB)
C_CONSTR = [220, 50, 47]    # under-construction road  (red)
C_BUILT = [38, 139, 210]    # operational road         (blue)
C_ISLAND = [133, 153, 0]    # island                   (green)
C_URBAN = [203, 145, 47]    # urban / built-up         (amber)


@st.cache_data
def load() -> pd.DataFrame:
    return pd.read_parquet(DATA / "cells.parquet")


def main() -> None:
    st.set_page_config("VN Imagery Coverage", layout="wide")
    st.title("🛰️ Vietnam Satellite-Imagery Coverage Planner")

    if not (DATA / "cells.parquet").exists():
        st.error("data/cells.parquet not found — run prep/04_build_cells.py first.")
        return
    df = load()

    sb = st.sidebar
    sb.header("Criteria")

    inc_urban = sb.checkbox("Urban / built-up", True)
    pct = sb.slider("Min built-up % of cell", 0, 100, 10, disabled=not inc_urban)

    inc_roads = sb.checkbox("Highways", True)
    classes = sb.multiselect("Road classes", ROAD_CLASSES, ROAD_CLASSES,
                             disabled=not inc_roads)
    r_built = sb.checkbox("· operational (built)", True, disabled=not inc_roads)
    r_constr = sb.checkbox("· under construction", True, disabled=not inc_roads)

    inc_islands = sb.checkbox("Islands (đặc khu)", True)
    isl_extent = sb.radio("Island extent", ["Land only", "Full zone (incl. sea)"],
                          disabled=not inc_islands,
                          help="Land only = OSM coastline land; Full = whole đặc khu polygon.")

    provs = sorted(df["province"].dropna().unique())
    sel_provs = sb.multiselect("Provinces (empty = all)", provs, [])

    sb.header("Cost")
    price = sb.number_input("Price $/km²", min_value=0.0, value=0.0, step=0.5)
    sb.text_input("Resolution label", "unknown")

    # ---- selection masks (always pandas Series) ----
    false = pd.Series(False, index=df.index)
    cls = set(classes)
    urban_m = (df["built_up_ratio"] * 100 >= pct) if inc_urban else false
    road_m = false.copy()
    if inc_roads:
        if r_built:
            road_m |= df["road_built"] & df["road_built_class"].isin(cls)
        if r_constr:
            road_m |= df["road_construction"] & df["road_constr_class"].isin(cls)
    if inc_islands:
        island_m = df["is_island_land"] if isl_extent == "Land only" else df["is_island"]
    else:
        island_m = false

    selected = urban_m | road_m | island_m
    if sel_provs:
        selected &= df["province"].isin(sel_provs)
    sel = df[selected].copy()

    # ---- headline metrics ----
    km2 = sel["cell_area_m2"].sum() / 1e6
    c1, c2, c3 = st.columns(3)
    c1.metric("Cells selected", f"{len(sel):,}")
    c2.metric("Coverage area", f"{km2:,.1f} km²")
    c3.metric("Est. cost", f"${km2 * price:,.0f}" if price else "—")

    # ---- breakdown by category ----
    cat_u = urban_m[selected]
    cat_r = road_m[selected]
    cat_i = island_m[selected]
    rows = [
        ("Urban / built-up", sel.loc[cat_u, "cell_area_m2"].sum() / 1e6),
        ("Highways", sel.loc[cat_r, "cell_area_m2"].sum() / 1e6),
        ("Islands", sel.loc[cat_i, "cell_area_m2"].sum() / 1e6),
    ]
    overlap = (cat_u.astype(int) + cat_r.astype(int) + cat_i.astype(int)) > 1
    rows.append(("(cells in ≥2 categories)", sel.loc[overlap, "cell_area_m2"].sum() / 1e6))
    st.subheader("By category (km², categories overlap)")
    st.dataframe(pd.DataFrame(rows, columns=["category", "km²"]).round(1),
                 hide_index=True, use_container_width=True)

    by_prov = (sel.groupby("province")["cell_area_m2"].sum() / 1e6
               ).sort_values(ascending=False).round(1)
    st.subheader("Top provinces (km²)")
    st.dataframe(by_prov.head(15).rename("km²"), use_container_width=True)

    # ---- map ----
    def color(r):
        if r["road_construction"] and road_m[r.name]:
            return C_CONSTR
        if r["road_built"] and road_m[r.name]:
            return C_BUILT
        if r["is_island"] and island_m[r.name]:
            return C_ISLAND
        return C_URBAN

    render = sel
    if len(sel) > MAX_RENDER:
        st.info(f"Showing a {MAX_RENDER:,}-cell sample on the map "
                f"(totals above use all {len(sel):,}).")
        render = sel.sample(MAX_RENDER, random_state=0)
    render = render.assign(rgb=render.apply(color, axis=1))

    layer = pdk.Layer(
        "H3HexagonLayer", render, get_hexagon="h3_id",
        get_fill_color="rgb", pickable=True, extruded=False, opacity=0.4,
    )
    view = pdk.ViewState(latitude=16.0, longitude=107.5, zoom=5)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view,
                             map_style="light",
                             tooltip={"text": "{province}\n{ward}"}))


if __name__ == "__main__":
    main()
