"""Maxspeed road-status dashboard (road-by-road, per the 2026-06-15 scope pivot).

Replaces the old H3 cell map with a **ranked road list**: every OSM national route
(quốc lộ QL.* / cao tốc CT.*) with its centerline km, maxspeed coverage %, gap km,
official state km (where known) + the diff, plus a connectivity/segment count and a
deep-link to an external relation analyzer for spot-checking. Sortable/filterable.
Then baseline coverage stats and a progress tracker.

The full multi-product dashboard (satellite / street-view / cost model + the H3 map)
stays in app.py. This is the focused single-problem cut.

Data (read-only):
  - traffic/maxspeed/baseline/route_coverage_result.json  (per-route, from route_coverage.py)
  - traffic/maxspeed/baseline/maxspeed_coverage_result.json (class totals)
Tracking state: dashboards/data/progress.json (maxspeed_km_filled + log; shared with app.py).

Run:  admin-poi/coverage/.venv/bin/streamlit run traffic/maxspeed/dashboard/app_maxspeed.py
"""
import datetime as dt
import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

REPO = Path(__file__).resolve().parents[3]
BASELINE = REPO / "traffic/maxspeed/baseline"
ROUTES = BASELINE / "route_coverage_result.json"
MAXSPEED = BASELINE / "maxspeed_coverage_result.json"
PROGRESS = REPO / "archive/dashboards/data/progress.json"  # shared with app.py

MAIN_CLASSES = ["motorway", "trunk", "primary", "secondary", "tertiary"]

# National highways + expressways. AH* (Asian Highway) and foreign G* (Chinese national
# roads at the border) are separate route relations laid over the *same* tarmac as QL./CT.
# routes — summing them double-counts physical road, so default the list to QL./CT. only.
VN_REF = re.compile(r"^(QL|CT)\.")

# Official centerline km from state sources, keyed by OSM ref — compared to the OSM
# centerline estimate to flag over/under-mapping. Extend as figures are verified.
# QL.1 ≈ 2,482 km (Hữu Nghị→Năm Căn); QL.14(A) ≈ 1,005 km. Source: vi.wikipedia.org.
OFFICIAL_KM = {"QL.1": 2482, "QL.14": 1005}

st.set_page_config(page_title="VN Maxspeed Tracker", layout="wide")


# ----------------------------------------------------------------- data loaders
@st.cache_data
def load_routes():
    df = pd.DataFrame(json.loads(ROUTES.read_text()))
    df["is_national"] = df["ref"].str.match(VN_REF)
    df["official_km"] = df["ref"].map(OFFICIAL_KM)
    df["diff_km"] = (df["centerline_km"] - df["official_km"]).round(1)
    # maxspeed_km and km are both carriageway km, so their ratio is the coverage; apply
    # it to centerline to get a comparable gap.
    df["gap_km"] = (df["centerline_km"] * (1 - df["pct_maxspeed"] / 100)).round(1)
    df["rid0"] = df["rel_ids"].map(lambda r: r[0] if r else None)
    return df


@st.cache_data
def load_maxspeed():
    d = json.loads(MAXSPEED.read_text())
    c = d["classes"]
    rows = [{"class": k, "total_km": c[k]["total_km"], "have_km": c[k]["maxspeed_km"],
             "missing_km": c[k]["total_km"] - c[k]["maxspeed_km"],
             "pct_have": 100 * c[k]["maxspeed_km"] / c[k]["total_km"]} for k in MAIN_CLASSES]
    return pd.DataFrame(rows)


def load_progress():
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text())
    return {"maxspeed_km_filled": 0, "sat_km2_bought": 0, "sv_km_captured": 0, "log": []}


def save_progress(p):
    PROGRESS.write_text(json.dumps(p, indent=2))


# ----------------------------------------------------------------- page
st.title("🚦 Vietnam Maxspeed Tracker")
st.caption("Road-by-road speed-limit coverage on the national network (quốc lộ / cao tốc) "
           "— centerline km vs official, the maxspeed gap, and progress.")

mx = load_maxspeed()
total_km = mx["total_km"].sum()
have_km = mx["have_km"].sum()
missing_km = mx["missing_km"].sum()

tab_roads, tab_stats, tab_track = st.tabs(["🛣️ Roads", "📊 Coverage", "✅ Tracking"])

# ---- Roads (the worklist) ----
with tab_roads:
    rt = load_routes()
    ctl = st.columns(4)
    national_only = ctl[0].checkbox(
        "National refs only (QL./CT.)", True,
        help="exclude Asian Highway AH* and foreign G* relations that overlap the same tarmac")
    min_km = ctl[1].slider("Min centerline km", 0, 500, 0, 10)
    only_gap = ctl[2].checkbox("Only roads with a maxspeed gap", False)
    q = ctl[3].text_input("Search ref / name")

    sel = rt.copy()
    if national_only:
        sel = sel[sel["is_national"]]
    sel = sel[sel["centerline_km"] >= min_km]
    if only_gap:
        sel = sel[sel["pct_maxspeed"] < 100]
    if q:
        sel = sel[sel["ref"].str.contains(q, case=False, na=False)
                  | sel["name"].str.contains(q, case=False, na=False)]
    sel = sel.sort_values("centerline_km", ascending=False)

    m = st.columns(4)
    m[0].metric("Roads", f"{len(sel):,}")
    m[1].metric("Centerline km", f"{sel['centerline_km'].sum():,.0f}")
    cov = 100 * sel["maxspeed_km"].sum() / max(sel["km"].sum(), 1)
    m[2].metric("Has maxspeed", f"{cov:.0f}%")
    m[3].metric("Maxspeed gap", f"{sel['gap_km'].sum():,.0f} km")

    disp = sel.assign(
        analyze=sel["rid0"].map(
            lambda r: f"https://ra.osmsurround.org/analyzeRelation?relationId={r}" if r else None),
        osm=sel["rid0"].map(
            lambda r: f"https://www.openstreetmap.org/relation/{r}" if r else None),
    )[["ref", "name", "classes", "centerline_km", "official_km", "diff_km",
       "pct_maxspeed", "gap_km", "components", "n_relations", "analyze", "osm"]]
    st.dataframe(
        disp, hide_index=True, width="stretch",
        column_config={
            "ref": "ref",
            "name": "name",
            "classes": "classes",
            "centerline_km": st.column_config.NumberColumn("centerline km", format="%.0f"),
            "official_km": st.column_config.NumberColumn("official km", format="%.0f"),
            "diff_km": st.column_config.NumberColumn("Δ vs official", format="%+.0f"),
            "pct_maxspeed": st.column_config.ProgressColumn(
                "% maxspeed", min_value=0, max_value=100, format="%.0f%%"),
            "gap_km": st.column_config.NumberColumn("gap km", format="%.0f"),
            "components": st.column_config.NumberColumn(
                "segments", help="connected components of member ways — >1 = gaps "
                                 "or split carriageways to inspect"),
            "n_relations": st.column_config.NumberColumn("rels"),
            "analyze": st.column_config.LinkColumn(
                "analyze", display_text="osmsurround",
                help="gap/connectivity analysis (replaces the retired OSM Route Manager)"),
            "osm": st.column_config.LinkColumn("OSM", display_text="relation"),
        })
    st.caption("Centerline km = member carriageway km with divided (oneway) sections halved "
               "— comparable to official road-length stats. `% maxspeed` and `gap km` are on "
               "the carriageway basis. `segments` >1 flags route relations with gaps or split "
               "carriageways; click **osmsurround** to inspect. Source: route_coverage.py.")

# ---- Coverage ----
with tab_stats:
    c = st.columns(3)
    c[0].metric("Tertiary+ network", f"{total_km:,.0f} km")
    c[1].metric("Has maxspeed", f"{have_km:,.0f} km", f"{100*have_km/total_km:.1f}%")
    c[2].metric("Missing", f"{missing_km:,.0f} km", f"{100*missing_km/total_km:.1f}%")
    st.progress(have_km / total_km, text=f"{100*have_km/total_km:.1f}% of tertiary+ has a speed limit")
    show = mx.copy()
    show["pct_have"] = show["pct_have"].round(1)
    st.dataframe(show.rename(columns={
        "class": "class", "total_km": "total km", "have_km": "has maxspeed km",
        "missing_km": "missing km", "pct_have": "% covered"}),
        hide_index=True, width="stretch")
    st.bar_chart(mx.set_index("class")[["have_km", "missing_km"]])

# ---- Tracking ----
with tab_track:
    prog = load_progress()
    done = prog.get("maxspeed_km_filled", 0)
    st.metric("Maxspeed km filled so far", f"{done:,} km",
              f"{100*done/missing_km:.1f}% of the {missing_km:,.0f} km gap")
    st.progress(min(done / missing_km, 1.0))
    with st.form("update"):
        new_done = st.number_input("Update total maxspeed km filled", min_value=0,
                                   value=int(done), step=100)
        if st.form_submit_button("Save"):
            prog["maxspeed_km_filled"] = int(new_done)
            prog.setdefault("log", []).append({
                "date": dt.date.today().isoformat(), "maxspeed_km_filled": int(new_done)})
            save_progress(prog)
            st.success("Saved.")
            st.rerun()
    if prog.get("log"):
        hist = pd.DataFrame(prog["log"])
        st.line_chart(hist.set_index("date")["maxspeed_km_filled"])
