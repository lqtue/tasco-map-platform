"""
Vietnam Map-Data Enrichment — Decision & Tracking Dashboard.

One front-facing **H3 map** carrying every criterion (built-up, road network with
maxspeed & name coverage, islands) whose filters drive a live **cost estimate**,
plus per-product cost tabs (maxspeed, satellite, street view, street-name) and a
progress tracker.

Run:  coverage/.venv/bin/streamlit run osm-enrichment/dashboard/app.py

Data sources (read-only):
  - osm-enrichment/baseline/maxspeed_coverage_result.json   (maxspeed coverage)
  - osm-enrichment/baseline/name_coverage_result.json       (street-name, tertiary+)
  - osm-enrichment/baseline/name_coverage_by_province.json  (street-name by province)
  - osm-enrichment/baseline/name_coverage_full_result.json  (all classes incl resi)
  - coverage/data/cells.parquet                             (H3 res-10 master cells)
  - coverage/data/road_coverage_cells.parquet               (per-cell maxspeed/name km)
  - osm-enrichment/dashboard/data/sat_envelope.json         (precomputed buy km²)
Tracking state is written to osm-enrichment/dashboard/data/progress.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

REPO = Path(__file__).resolve().parents[2]
BASELINE = REPO / "osm-enrichment/baseline"
COVERAGE_DATA = REPO / "coverage/data"
MAXSPEED = BASELINE / "maxspeed_coverage_result.json"
NAME = BASELINE / "name_coverage_result.json"
NAME_PROV = BASELINE / "name_coverage_by_province.json"
NAME_FULL = BASELINE / "name_coverage_full_result.json"
SAT = Path(__file__).resolve().parent / "data/sat_envelope.json"
PROGRESS = Path(__file__).resolve().parent / "data/progress.json"

MAIN_CLASSES = ["motorway", "trunk", "primary", "secondary", "tertiary"]
MAX_RENDER = 250_000  # cap hexes sent to the browser

# criteria colours (RGB)
C_MS = [220, 50, 47]      # maxspeed gap   (red)
C_NAME = [108, 71, 173]   # name gap       (purple)
C_URBAN = [203, 145, 47]  # urban built-up (amber)
C_ROAD = [38, 139, 210]   # road, no gap   (blue)
C_ISLAND = [133, 153, 0]  # island land    (green)

st.set_page_config(page_title="VN Enrichment — Map, Decision & Tracking", layout="wide")


# ---------------------------------------------------------------- data loaders
@st.cache_data
def load_maxspeed():
    d = json.loads(MAXSPEED.read_text())
    c = d["classes"]
    rows = []
    for k in MAIN_CLASSES:
        total, have = c[k]["total_km"], c[k]["maxspeed_km"]
        rows.append({"class": k, "total_km": total, "have_km": have,
                     "missing_km": total - have, "pct_have": 100 * have / total})
    return pd.DataFrame(rows)


@st.cache_data
def load_name():
    res = json.loads(NAME.read_text())
    cls = pd.DataFrame([
        {"class": k, **v} for k, v in res["per_class"].items()
    ])
    prov = pd.DataFrame(json.loads(NAME_PROV.read_text()))
    full = json.loads(NAME_FULL.read_text())
    return {"res": res, "class": cls, "prov": prov, "full": full}


@st.cache_data
def load_sat():
    return json.loads(SAT.read_text())


@st.cache_data
def load_cells():
    """Master H3 cells unioned with the per-cell road-coverage sidecar.

    cells.parquet only holds urban + strategic-road + island cells, so most
    tertiary/secondary road cells are absent — they're appended from the sidecar
    (which carries their geometry + province) as otherwise-empty rows.
    """
    base = pd.read_parquet(COVERAGE_DATA / "cells.parquet")
    metric_cols = ["road_km", "maxspeed_km", "name_km", "lanes_km", "top_class"]
    rcp = COVERAGE_DATA / "road_coverage_cells.parquet"
    if rcp.exists():
        rc = pd.read_parquet(rcp)
        new = rc[~rc["h3_id"].isin(base["h3_id"])].copy()
        if len(new):
            new["built_up_area_m2"] = 0.0
            new["building_count"] = 0
            new["road_built"] = False
            new["road_built_class"] = None
            new["road_construction"] = False
            new["road_constr_class"] = None
            new["is_island"] = False
            new["is_island_land"] = False
            new["built_up_ratio"] = 0.0
            new = new.reindex(columns=base.columns)  # drop metric cols; keep geo+admin
            base = pd.concat([base, new], ignore_index=True)
        base = base.merge(rc[["h3_id"] + metric_cols], on="h3_id", how="left")
    for col in ("road_km", "maxspeed_km", "name_km", "lanes_km"):
        if col not in base:
            base[col] = 0.0
        base[col] = base[col].fillna(0.0)
    if "top_class" not in base:
        base["top_class"] = None
    base["maxspeed_gap_km"] = (base["road_km"] - base["maxspeed_km"]).clip(lower=0)
    base["name_gap_km"] = (base["road_km"] - base["name_km"]).clip(lower=0)
    return base


def load_progress():
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text())
    return {"maxspeed_km_filled": 0, "sat_km2_bought": 0, "sv_km_captured": 0, "log": []}


def save_progress(p):
    PROGRESS.write_text(json.dumps(p, indent=2))


def manhours(km, km_per_hour, rate_vnd, fx):
    """(man-hours, ₫ cost, $ cost) to hand-process `km` at a throughput + rate."""
    mh = km / km_per_hour if km_per_hour else 0.0
    vnd = mh * rate_vnd
    return mh, vnd, (vnd / fx if fx else 0.0)


def mh_only(km, km_per_hour):
    return km / km_per_hour if km_per_hour else 0.0


def _heat(vals, lo, hi):
    v = np.clip(np.asarray(vals, dtype=float), 0, 1)
    return [[int(lo[i] + (hi[i] - lo[i]) * x) for i in range(3)] for x in v]


def cell_colors(d, colorby, pct):
    """Per-row RGB for the H3 layer; either a heat ramp or criteria priority."""
    if colorby == "Built-up heat":
        return _heat(d["built_up_ratio"].clip(0, 1), [255, 237, 160], [189, 0, 38])
    if colorby == "Maxspeed-gap heat":
        return _heat(d["maxspeed_gap_km"] / max(d["maxspeed_gap_km"].max(), 1e-6),
                     [239, 243, 255], [8, 48, 107])
    if colorby == "Name-gap heat":
        return _heat(d["name_gap_km"] / max(d["name_gap_km"].max(), 1e-6),
                     [252, 237, 247], [84, 39, 143])
    # "Criteria": priority maxspeed-gap > name-gap > urban > road > island
    g_ms = (d["maxspeed_gap_km"] > 0).values
    g_nm = (d["name_gap_km"] > 0).values
    g_ur = (d["built_up_ratio"] * 100 >= pct).values
    g_rd = (d["road_km"] > 0).values
    out = []
    for i in range(len(d)):
        if g_ms[i]:
            out.append(C_MS)
        elif g_nm[i]:
            out.append(C_NAME)
        elif g_ur[i]:
            out.append(C_URBAN)
        elif g_rd[i]:
            out.append(C_ROAD)
        else:
            out.append(C_ISLAND)
    return out


ms = load_maxspeed()
nm = load_name()
sat = load_sat()
missing_total = ms["missing_km"].sum()
have_total = ms["have_km"].sum()
network_total = ms["total_km"].sum()
no_name_tert = nm["res"]["no_name_km"]
no_name_full = nm["full"]["no_name_km"]


# phase scopes (street view priority = missing-maxspeed km by class group)
def miss(classes):
    return ms[ms["class"].isin(classes)]["missing_km"].sum()


P1 = miss(["motorway", "trunk", "primary"])
P2 = P1 + miss(["secondary"])
P3 = missing_total


# ----------------------------------------------------------------- sidebar levers
st.sidebar.header("⚙️ Levers (live)")

st.sidebar.subheader("💱 Currency")
fx = st.sidebar.number_input("FX — ₫ per $1", min_value=1000, value=25000, step=500)

st.sidebar.subheader("🛰️ Satellite")
thr = st.sidebar.select_slider("Urban built-up threshold", options=["0.00", "0.05", "0.10", "0.20", "0.30"], value="0.10")
incl_island = st.sidebar.checkbox("Include island land", value=True)
price_km2 = st.sidebar.number_input("Price $/km² (UP42/Skywatch — confirm)", min_value=0.0, value=8.0, step=0.5)

st.sidebar.subheader("🚦 Maxspeed review")
review_frac = st.sidebar.slider("% missing needing manual review", 0, 100, 15) / 100
ms_kmph = st.sidebar.slider("km reviewed / man-hour", 1, 30, 6)
ms_rate = st.sidebar.select_slider("₫ / man-hour (review)", options=[30000, 40000, 100000],
                                   value=40000, format_func=lambda v: f"₫{v:,}")

st.sidebar.subheader("📛 Street-name fill")
name_kmph = st.sidebar.slider("km named / man-hour", 1, 20, 4)
name_rate = st.sidebar.select_slider("₫ / man-hour (naming)", options=[30000, 40000, 100000],
                                     value=40000, format_func=lambda v: f"₫{v:,}")

st.sidebar.subheader("📷 Street view")
target_months = st.sidebar.slider("Target deadline (months)", 1.0, 12.0, 2.0, step=0.5)
drivers = st.sidebar.slider("Active drivers", 50, 1000, 95, step=5)
km_per_mo = st.sidebar.slider("New road km / driver / month", 50, 800, 800, step=50)
mb_per_km = st.sidebar.slider("Capture size (MB/km)", 20, 400, 100, step=10)
overlap = st.sidebar.slider("Re-drive overlap factor", 1.0, 2.0, 1.3, step=0.1)
incl_resi = st.sidebar.checkbox("Include residential streets", value=False)
resi_mult = st.sidebar.slider("Residential multiplier (×tertiary+)", 1.5, 4.0, 2.5, step=0.5, disabled=not incl_resi)
st.sidebar.caption("Street-view cost")
cost_per_tb = st.sidebar.number_input("Storage $/TB (one-off)", min_value=0.0, value=20.0, step=5.0)
tasked_frac = st.sidebar.slider("Long-tail % needing tasked driving", 0, 60, 30) / 100
incentive_km = st.sidebar.number_input("Incentive $/tasked-km (fuel/bonus)", min_value=0.0, value=0.08, step=0.01)
buy_dashcams = st.sidebar.checkbox("Buy dashcams (else use phones)", value=False)
dashcam_unit = st.sidebar.number_input("Dashcam $/unit", min_value=0.0, value=60.0, step=10.0, disabled=not buy_dashcams)


# ----------------------------------------------------------------- derived numbers
key = "union_landisland" if incl_island else "union_no_island"
sat_km2 = sat["thresholds"][thr][key]
sat_cost = sat_km2 * price_km2

sv_scope_km = P3 * resi_mult if incl_resi else P3
sv_eff_km = sv_scope_km * overlap                          # km actually driven (with re-drive)
sv_tb = sv_eff_km * mb_per_km / 1e6                        # storage
sv_months = sv_eff_km / (drivers * km_per_mo)              # time at current fleet
sv_storage_cost = sv_tb * cost_per_tb
sv_incentive_cost = sv_scope_km * tasked_frac * incentive_km
sv_dashcam_cost = drivers * dashcam_unit if buy_dashcams else 0
sv_cost = sv_storage_cost + sv_incentive_cost + sv_dashcam_cost
req_throughput = sv_eff_km / target_months                # fleet new-km / month needed
req_drivers = req_throughput / km_per_mo                  # at current per-driver rate
feasible = drivers >= req_drivers

ms_review_km = missing_total * review_frac
ms_mh, ms_vnd, ms_usd = manhours(ms_review_km, ms_kmph, ms_rate, fx)
name_mh, name_vnd, name_usd = manhours(no_name_tert, name_kmph, name_rate, fx)
total_capex = sat_cost + sv_cost + ms_usd + name_usd


# ----------------------------------------------------------------- tabs
st.title("🗺️ Vietnam Map-Data Enrichment — Map, Decision & Tracking")
st.caption("Selling point: timely lane-turn / speed-limit / traffic-sign alerts → data layers needed → cost → time → progress.  Source: OSM extract 2026-06-06 + coverage H3 pipeline.")

tab_map, tab_dec, tab_ms, tab_name, tab_sat, tab_sv, tab_track = st.tabs(
    ["🗺️ Map", "📊 Decision", "🚦 Maxspeed", "📛 Street-name", "🛰️ Satellite", "📷 Street view", "✅ Tracking"])

# ---- Map (front-facing) ----
with tab_map:
    st.subheader("National H3 grid — every criterion on one map")
    cells = load_cells()
    has_road = cells["road_km"].sum() > 0
    if not has_road:
        st.warning("`coverage/data/road_coverage_cells.parquet` missing or empty — "
                   "run `coverage/prep/05_road_coverage.py` to light up the maxspeed/name layers. "
                   "Built-up / island layers still work.")

    ctl = st.columns(6)
    inc_urban = ctl[0].checkbox("Urban built-up", True)
    pct = ctl[0].slider("Min built-up %", 0, 100, 10, disabled=not inc_urban)
    inc_ms = ctl[1].checkbox("Maxspeed gap", True, help="cells with tertiary+ road lacking maxspeed")
    inc_nm = ctl[2].checkbox("Name gap", True, help="cells with tertiary+ road lacking a name")
    inc_road = ctl[3].checkbox("Any tertiary+ road", False)
    cls_sel = ctl[3].multiselect("Classes", MAIN_CLASSES, MAIN_CLASSES, disabled=not inc_road)
    inc_island = ctl[4].checkbox("Island land", False)
    colorby = ctl[5].radio("Colour by", ["Criteria", "Built-up heat", "Maxspeed-gap heat", "Name-gap heat"])

    provs = sorted(cells["province"].dropna().unique())
    sel_provs = st.multiselect("Provinces (empty = all of Vietnam)", provs, [])

    # ---- masks (always pandas Series) ----
    false = pd.Series(False, index=cells.index)
    m_urban = (cells["built_up_ratio"] * 100 >= pct) if inc_urban else false
    m_ms = (cells["maxspeed_gap_km"] > 0) if inc_ms else false
    m_nm = (cells["name_gap_km"] > 0) if inc_nm else false
    if inc_road:
        m_road = (cells["road_km"] > 0) & cells["top_class"].isin(cls_sel)
    else:
        m_road = false
    m_isl = cells["is_island_land"] if inc_island else false

    selected = m_urban | m_ms | m_nm | m_road | m_isl
    if sel_provs:
        selected &= cells["province"].isin(sel_provs)
    sel = cells[selected]

    # ---- headline metrics over the full selection ----
    km2 = sel["cell_area_m2"].sum() / 1e6
    sel_road_km = sel["road_km"].sum()
    sel_ms_gap = sel["maxspeed_gap_km"].sum()
    sel_name_gap = sel["name_gap_km"].sum()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Cells lit", f"{len(sel):,}")
    m2.metric("Area (satellite)", f"{km2:,.0f} km²")
    m3.metric("Tertiary+ road", f"{sel_road_km:,.0f} km")
    m4.metric("Maxspeed gap", f"{sel_ms_gap:,.0f} km")
    m5.metric("Name gap", f"{sel_name_gap:,.0f} km")

    # ---- live cost estimate for the current selection ----
    sat_c = km2 * price_km2
    _, _, ms_c = manhours(sel_ms_gap * review_frac, ms_kmph, ms_rate, fx)
    _, _, name_c = manhours(sel_name_gap, name_kmph, name_rate, fx)
    sv_mo = sel_road_km * overlap / (drivers * km_per_mo) if sel_road_km else 0
    sel_total = sat_c + ms_c + name_c
    st.markdown("##### 💵 Live cost for this selection")
    cc = st.columns(4)
    cc[0].metric("Satellite", f"${sat_c:,.0f}", f"{km2:,.0f} km² × ${price_km2:.1f}")
    cc[1].metric("Maxspeed review", f"${ms_c:,.0f}", f"{mh_only(sel_ms_gap*review_frac, ms_kmph):,.0f} man-hr")
    cc[2].metric("Name fill", f"${name_c:,.0f}", f"{mh_only(sel_name_gap, name_kmph):,.0f} man-hr")
    cc[3].metric("Street-view time", f"{sv_mo:.1f} mo", f"{sel_road_km*overlap:,.0f} eff-km")
    st.caption(f"Selection cash (sat + review + naming) = **${sel_total:,.0f}** · street-view is time/effort, costed in its own tab. "
               f"Rates from sidebar: review ₫{ms_rate:,}/hr @ {ms_kmph} km/hr · naming ₫{name_rate:,}/hr @ {name_kmph} km/hr · FX ₫{fx:,}/$.")

    # ---- by-category breakdown (categories overlap) ----
    rows = [
        ("Urban / built-up", float(sel.loc[m_urban[selected], "cell_area_m2"].sum() / 1e6), None),
        ("Maxspeed gap", None, float(sel.loc[m_ms[selected], "maxspeed_gap_km"].sum())),
        ("Name gap", None, float(sel.loc[m_nm[selected], "name_gap_km"].sum())),
        ("Island land", float(sel.loc[m_isl[selected], "cell_area_m2"].sum() / 1e6), None),
    ]
    st.dataframe(pd.DataFrame(rows, columns=["criterion", "km² (area)", "km (road gap)"]),
                 hide_index=True, width="stretch")

    # ---- map ----
    if len(sel):
        render = sel
        if len(sel) > MAX_RENDER:
            st.info(f"Showing a {MAX_RENDER:,}-cell sample on the map (metrics above use all {len(sel):,}).")
            render = sel.sample(MAX_RENDER, random_state=0)
        # send ONLY the columns the layer + tooltip need — the full row schema
        # (~23 cols × 250k) blows past Streamlit's 200 MB message cap.
        slim = pd.DataFrame({
            "h3_id": render["h3_id"].values,
            "rgb": cell_colors(render, colorby, pct),
            "province": render["province"].fillna("—").values,
            "ward": render["ward"].fillna("—").values,
            "built_up_pct": (render["built_up_ratio"] * 100).round(1).values,
            "top_class": render["top_class"].fillna("—").values,
            "road_km_r": render["road_km"].round(2).values,
            "ms_km_r": render["maxspeed_km"].round(2).values,
            "name_km_r": render["name_km"].round(2).values,
        })
        layer = pdk.Layer("H3HexagonLayer", slim, get_hexagon="h3_id",
                          get_fill_color="rgb", pickable=True, extruded=False, opacity=0.45)
        view = pdk.ViewState(latitude=16.0, longitude=107.5, zoom=5)
        st.pydeck_chart(pdk.Deck(
            layers=[layer], initial_view_state=view, map_style="light",
            tooltip={"html": "<b>{province}</b> — {ward}<br/>"
                             "built-up {built_up_pct}% · class {top_class}<br/>"
                             "road {road_km_r} km · maxspeed {ms_km_r} · name {name_km_r}"}))
    else:
        st.info("No cells match — enable a criterion above.")

# ---- Decision ----
with tab_dec:
    st.markdown("### 🎯 The selling point")
    st.markdown(f"""
**Timely, lane-level driving alerts** — *"move to the right lane to turn"*, the current **speed limit**, and **traffic signs**
(no-overtaking, residential zone) — surfaced **before** the maneuver, not after. Competitors route; **we warn**.

To deliver this we need fresh, complete data layers across Vietnam's **tertiary+ network ({network_total:,.0f} km)**:

| Capability the driver gets | Data layer needed | How we acquire it |
|---|---|---|
| ⏱️ **Speed-limit alert** | `maxspeed` on every segment | Legal-rule layer (~\\$0) + imagery verify |
| 🧭 **Street-name / address** | `name` on every way | Address-vector fill → editor approve (Rapid-style) |
| ↪️ **Right-lane / turn-lane alert** | lane count + turn geometry | Street-view capture → CNN lane inference (RoadTagger) |
| 🚸 **Traffic-sign alert** | sign position + value | Street-view + satellite detection |
""")
    a, b, c = st.columns(3)
    a.metric("→ To do it", f"{target_months:.0f}-mo capture", f"{req_drivers:,.0f} drivers + {sat_km2:,.0f} km² sat")
    b.metric("→ Cost", f"${total_capex:,.0f}", "no external data purchase")
    c.metric("→ Time", f"{sv_months:.1f} months", "to national tertiary+ coverage")
    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Maxspeed missing", f"{missing_total:,.0f} km", f"{100*missing_total/network_total:.1f}% of tertiary+")
    c2.metric("Street-name missing", f"{no_name_tert:,.0f} km", f"{100*no_name_tert/nm['res']['total_km']:.1f}% of tertiary+")
    c3.metric("Satellite to buy", f"{sat_km2:,.0f} km²", f"${sat_cost:,.0f}")
    c4.metric("Total capex ask", f"${total_capex:,.0f}", "sat + review + naming + street-view")

    st.subheader("Investment summary")
    summ = pd.DataFrame([
        {"Data product": "Maxspeed", "Scope": f"{missing_total:,.0f} km missing",
         "Acquisition": "Law layer ~100% ($0) + imagery verify",
         "External $": f"${ms_usd:,.0f}", "Note": f"{ms_mh:,.0f} man-hr @ ₫{ms_rate:,}/hr"},
        {"Data product": "Street-name", "Scope": f"{no_name_tert:,.0f} km no-name",
         "Acquisition": "Address-vector fill + editor approve",
         "External $": f"${name_usd:,.0f}", "Note": f"{name_mh:,.0f} man-hr @ ₫{name_rate:,}/hr"},
        {"Data product": "Satellite imagery", "Scope": f"{sat_km2:,.0f} km² (urban≥{float(thr):.0%})",
         "Acquisition": "UP42 / Skywatch", "External $": f"${sat_cost:,.0f}", "Note": f"@ ${price_km2:.1f}/km²"},
        {"Data product": "Street view", "Scope": f"{sv_scope_km:,.0f} km ({'+resi' if incl_resi else 'tertiary+'})",
         "Acquisition": "Internal crowdsource (KPI/Loyalty)", "External $": f"${sv_cost:,.0f}", "Note": f"{sv_tb:.1f} TB storage"},
    ])
    st.dataframe(summ, hide_index=True, width="stretch")
    st.info("⚠️ Boxes to confirm before deck: **$/km²** (Vũ/procurement) · **man-hour rate + throughput** (Anh/HR) · **incentive** (Anh/HR). FX ₫/$ in sidebar.")

    with st.expander("📐 Methodology — how each number is derived"):
        st.markdown(f"""
**Data sources.** Maxspeed + name from OSM extract 2026-06-06 (`maxspeed_coverage_result.json`, `name_coverage_*`), geodesic WGS84 km per highway class. Satellite km² + the front map from the H3 res-10 coverage pipeline (`cells.parquet` + `road_coverage_cells.parquet`). All levers in the sidebar.

**Maxspeed missing** = Σ(total−have) over motorway…tertiary = **{missing_total:,.0f} km**. **Street-name missing** = tertiary+ ways with no `name` = **{no_name_tert:,.0f} km**.

**Man-hour cost** = (km × review-fraction) ÷ throughput × ₫rate, ÷ FX → $. Maxspeed: {ms_review_km:,.0f} km → **{ms_mh:,.0f} man-hr** → **${ms_usd:,.0f}**. Naming: {no_name_tert:,.0f} km → **{name_mh:,.0f} man-hr** → **${name_usd:,.0f}**.

**Total capex** = satellite + street-view + maxspeed review + name fill = **${total_capex:,.0f}**. No external *data* purchase — only imagery + human man-hours.
""")

# ---- Maxspeed ----
with tab_ms:
    st.subheader(f"Coverage by class — {have_total:,.0f} km have / {missing_total:,.0f} km missing ({100*have_total/network_total:.1f}% done)")
    show = ms.copy()
    show["pct_have"] = show["pct_have"].round(1)
    st.dataframe(show.style.format({"total_km": "{:,.0f}", "have_km": "{:,.0f}",
                                    "missing_km": "{:,.0f}", "pct_have": "{:.1f}%"}),
                 hide_index=True, width="stretch")
    st.bar_chart(ms.set_index("class")[["have_km", "missing_km"]], color=["#268bd2", "#dc322f"])

    st.markdown("#### 🧮 Manual-review man-hours & cost")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Need review", f"{ms_review_km:,.0f} km", f"{100*review_frac:.0f}% of missing")
    r2.metric("Man-hours", f"{ms_mh:,.0f} hr", f"@ {ms_kmph} km/hr")
    r3.metric("Cost ₫", f"₫{ms_vnd:,.0f}", f"@ ₫{ms_rate:,}/hr")
    r4.metric("Cost $", f"${ms_usd:,.0f}", f"FX ₫{fx:,}/$")
    st.markdown(f"""
**Priority phases (high-value first):**
- **P1** motorway+trunk+primary: **{P1:,.0f} km** missing
- **P2** + secondary: **{P2:,.0f} km**
- **P3** full tertiary+: **{P3:,.0f} km**

Law layer (Quân) assigns candidate maxspeed to ~100% of missing km at **$0**; only the **{100*review_frac:.0f}%** of exceptions reach a human, at **{ms_kmph} km/man-hour** (₫{ms_rate:,}/hr → community vs pro). Motorway first = self-do / higher rate.
""")
    with st.expander("📐 Methodology — maxspeed coverage"):
        st.markdown(f"""
**Source.** `osm-enrichment/baseline/run.sh`: Geofabrik Vietnam PBF → `osmium tags-filter` to tertiary+ highways → per-way length via pyproj `Geod.line_length` (**geodesic WGS84 km**).

**"tertiary+"** = motorway, trunk, primary, secondary, tertiary (+`_link`). **"has maxspeed"** = the tag *exists*, not that it's correct.

**Review cost** = missing_km × review% ÷ (km/man-hour) × ₫rate ÷ FX = {ms_review_km:,.0f} km → {ms_mh:,.0f} man-hr → ${ms_usd:,.0f}. The meeting's rates: ₫30k/40k community, ₫100k pro MapOps.
""")

# ---- Street-name ----
with tab_name:
    res = nm["res"]
    st.subheader(f"Street-name coverage — {res['named_km']:,.0f} km named / {no_name_tert:,.0f} km no-name "
                 f"({res['pct_named']:.1f}% of tertiary+ {res['total_km']:,.0f} km)")
    st.caption("Anh's task: from address/POI runs (\"14, 16 … ngõ 66 Trần Hưng Đạo\") build a road vector → "
               "*success* a candidate name onto the empty OSM way ID → editor approves (Rapid-style). Confidence "
               "by majority address; outliers flagged. Address-vector length recommends way splits.")

    nc1, nc2, nc3, nc4 = st.columns(4)
    nc1.metric("No-name (tertiary+)", f"{no_name_tert:,.0f} km")
    nc2.metric("Fill man-hours", f"{name_mh:,.0f} hr", f"@ {name_kmph} km/hr")
    nc3.metric("Cost ₫", f"₫{name_vnd:,.0f}", f"@ ₫{name_rate:,}/hr")
    nc4.metric("Cost $", f"${name_usd:,.0f}", f"FX ₫{fx:,}/$")

    st.markdown("**By class (tertiary+):**")
    cls = nm["class"].copy()
    cls["pct_named"] = 100 * cls["named_km"] / cls["total_km"]
    st.dataframe(cls.style.format({"total_km": "{:,.0f}", "named_km": "{:,.0f}",
                                   "no_name_km": "{:,.0f}", "pct_named": "{:.1f}%"}),
                 hide_index=True, width="stretch")

    st.markdown("**By province — worst-named first (MapOps prioritisation):**")
    prov = nm["prov"].sort_values("no_name_km", ascending=False)
    st.dataframe(prov.style.format({"total_km": "{:,.0f}", "named_km": "{:,.0f}",
                                    "no_name_km": "{:,.0f}", "pct_named": "{:.1f}%"}),
                 hide_index=True, width="stretch", height=320)
    st.info(f"HCMC is essentially done (90% named); Hà Nội ~72%. The backlog is north-central + northern-mountain "
            f"provinces (Thanh Hóa, Tuyên Quang, Cao Bằng ~39%) — where Google/Grab don't cover. "
            f"Residential + service nationally adds **{no_name_full - no_name_tert:,.0f} km** more no-name "
            f"(ngõ/hẻm tagged `service`) — kept off the cell map by design.")

# ---- Satellite ----
with tab_sat:
    st.subheader(f"Buy-envelope @ urban ≥ {float(thr):.0%}  →  {sat_km2:,.0f} km²  ·  ${sat_cost:,.0f}")
    fxc = sat["components_fixed_km2"]
    comp = pd.DataFrame([
        {"Component": f"Urban (built-up ≥ {float(thr):.0%})", "km²": sat["thresholds"][thr]["urban"]},
        {"Component": "Road corridor (operational)", "km²": fxc["road_built"]},
        {"Component": "Road corridor (construction)", "km²": fxc["road_constr"]},
        {"Component": "Island land" if incl_island else "Island land (excluded)", "km²": fxc["island_land"] if incl_island else 0},
        {"Component": "= UNION (dedup)", "km²": sat_km2},
    ])
    st.dataframe(comp.style.format({"km²": "{:,.0f}"}), hide_index=True, width="stretch")
    st.caption(f"Vietnam ≈ 331,000 km² → buying ~{100*sat_km2/331000:.1f}%. Island full-zone = {fxc['island_zone']:,.0f} km² (mostly open sea) — using {fxc['island_land']:,.0f} km² honest land.")

    st.markdown("**Price sensitivity (at current threshold):**")
    sens = pd.DataFrame([{"$/km²": p, "Total $": sat_km2 * p} for p in [3, 5, 8, 12, 15]])
    st.dataframe(sens.style.format({"$/km²": "${:.0f}", "Total $": "${:,.0f}"}), hide_index=True)

    with st.expander("📐 Methodology — satellite buy-envelope"):
        st.markdown(f"""
**Source.** Vietnam tiled with Uber **H3 res-10** (~16,470 m²/cell) **only around 3 targets** (sparse, ~5M cells): urban built-up (Google Open Buildings v3 centroids, conf ≥ 0.65), strategic road corridors (OSM motorway/trunk/primary, built + construction), islands.

**Buy-envelope** = **union** of {{urban ≥ threshold}} ∪ {{road corridor}} ∪ {{island land}}, deduplicated = **{sat_km2:,.0f} km²**. **Cost** = envelope km² × $/km² (archive ~\\$3–8, sub-meter tasking ~\\$12–15 — confirm with UP42/Skywatch). At 0.10 × \\$12 ≈ \\$250k (whole-country max).
""")

# ---- Street view ----
with tab_sv:
    st.subheader(f"Coverage plan — {sv_months:.1f} months · {sv_tb:.1f} TB · ${sv_cost:,.0f} total")

    st.markdown(f"#### 🎯 Can we finish in {target_months:.0f} months?")
    fc1, fc2, fc3 = st.columns(3)
    fc1.metric("Drivers needed", f"{req_drivers:,.0f}", f"have {drivers} ({drivers-req_drivers:+,.0f})")
    fc2.metric("Fleet throughput needed", f"{req_throughput:,.0f} km/mo", f"= {req_throughput/max(drivers,1):,.0f} km/driver/mo")
    fc3.metric("Finish at current fleet", f"{sv_months:.1f} months", "vs target " + f"{target_months:.0f}")
    if feasible:
        st.success(f"✅ **Feasible.** {drivers} drivers at {km_per_mo} new-km/mo finish {sv_scope_km:,.0f} km in {sv_months:.1f} months — "
                   f"within the {target_months:.0f}-month target. (Meeting plan: 95 drivers × 800 km/mo × 2 mo.)")
    else:
        st.warning(f"⚠️ **Tight.** Need {req_drivers:,.0f} drivers (have {drivers}) *or* raise per-driver rate to "
                   f"{req_throughput/max(drivers,1):,.0f} km/mo to hit {target_months:.0f} months. At current fleet it takes {sv_months:.1f} months.")
    st.caption("⚑ Long-tail risk: opportunistic capture covers popular roads fast but misses remote quốc lộ/tỉnh lộ. "
               "Full coverage needs **tasked driving** for the last ~10–20% — set the long-tail % in the sidebar. "
               "1 photo + 1 GPS + 1 IMU per second; GPS doubles as the historical speed profile for nationwide ETA.")

    st.markdown("#### Phases")
    rows = []
    for label, km in [("P1 motorway+trunk+primary", P1), ("P2 +secondary", P2), ("P3 full tertiary+", P3)]:
        eff = km * overlap
        rows.append({"Phase": label, "Drive-once km": km, "Eff km (×overlap)": eff,
                     "Storage TB": eff * mb_per_km / 1e6, "Months": eff / (drivers * km_per_mo)})
    if incl_resi:
        eff = P3 * resi_mult * overlap
        rows.append({"Phase": f"P3 + residential (×{resi_mult})", "Drive-once km": P3 * resi_mult,
                     "Eff km (×overlap)": eff, "Storage TB": eff * mb_per_km / 1e6,
                     "Months": eff / (drivers * km_per_mo)})
    st.dataframe(pd.DataFrame(rows).style.format({"Drive-once km": "{:,.0f}", "Eff km (×overlap)": "{:,.0f}",
                                                  "Storage TB": "{:.1f}", "Months": "{:.1f}"}),
                 hide_index=True, width="stretch")

    st.markdown("#### Cost breakdown")
    costdf = pd.DataFrame([
        {"Item": f"Storage ({sv_tb:.1f} TB @ ${cost_per_tb:.0f}/TB)", "$": sv_storage_cost},
        {"Item": f"Tasked-driving incentive ({sv_scope_km*tasked_frac:,.0f} km @ ${incentive_km:.2f})", "$": sv_incentive_cost},
        {"Item": f"Dashcams ({drivers} × ${dashcam_unit:.0f})" if buy_dashcams else "Dashcams (using phones)", "$": sv_dashcam_cost},
        {"Item": "= Total street-view cash", "$": sv_cost},
    ])
    st.dataframe(costdf.style.format({"$": "${:,.0f}"}), hide_index=True, width="stretch")
    st.caption(f"Assumptions: overlap ×{overlap}, {mb_per_km} MB/km, {drivers} drivers @ {km_per_mo} km/mo, "
               f"{100*tasked_frac:.0f}% tasked. Data is **collected, not purchased**.")

# ---- Tracking ----
with tab_track:
    st.subheader("Progress tracker")
    p = load_progress()
    c1, c2, c3 = st.columns(3)
    with c1:
        ms_done = st.number_input("Maxspeed km filled", 0, int(missing_total), int(p["maxspeed_km_filled"]), step=500)
        st.progress(min(ms_done / missing_total, 1.0), text=f"{ms_done:,} / {missing_total:,.0f} km ({100*ms_done/missing_total:.1f}%)")
    with c2:
        sat_done = st.number_input("Satellite km² bought", 0, int(sat_km2 * 2), int(p["sat_km2_bought"]), step=100)
        st.progress(min(sat_done / sat_km2, 1.0), text=f"{sat_done:,} / {sat_km2:,.0f} km² ({100*sat_done/sat_km2:.1f}%)")
    with c3:
        sv_done = st.number_input("Street view km captured", 0, int(P3 * 3), int(p["sv_km_captured"]), step=500)
        st.progress(min(sv_done / P3, 1.0), text=f"{sv_done:,} / {P3:,.0f} km ({100*sv_done/P3:.1f}%)")

    if st.button("💾 Save snapshot", type="primary"):
        p.update({"maxspeed_km_filled": ms_done, "sat_km2_bought": sat_done, "sv_km_captured": sv_done})
        p["log"].append({"date": str(pd.Timestamp.now().date()),
                         "maxspeed_km_filled": ms_done, "sat_km2_bought": sat_done, "sv_km_captured": sv_done})
        save_progress(p)
        st.success("Saved.")
        st.cache_data.clear()

    if p["log"]:
        st.subheader("History")
        hist = pd.DataFrame(p["log"])
        st.dataframe(hist, hide_index=True, width="stretch")
        st.line_chart(hist.set_index("date")[["maxspeed_km_filled", "sv_km_captured"]])
