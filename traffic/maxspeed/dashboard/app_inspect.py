"""Live OSM route inspector + temporary maxspeed editor (render.pl-style, but live + editable).

Fetch a national route by ref **straight from Overpass (live OSM)**, draw its member ways on a
map colored by maxspeed presence — like the retired OSM Route Manager
(osm.mueschelsoft.de/cgi-bin/render.pl?relref=...) — then edit maxspeed / lanes / median per way
and stage the proposed tags to a **local temp worklist** (data/route_edits.json).

Saving is **local only** — nothing is written to OSM. Operators apply the staged edits in iD with
street-view evidence in the changeset (2026-06-15 scope pivot). Lanes + median (dải phân cách) are
captured alongside maxspeed because a speed backed by morphology is harder to dispute than bare
maxspeed.

Run: admin-poi/coverage/.venv/bin/streamlit run traffic/maxspeed/dashboard/app_inspect.py
"""
import json
from pathlib import Path

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st
from pyproj import Geod

GEOD = Geod(ellps="WGS84")
OVERPASS = "https://overpass-api.de/api/interpreter"
UA = {"User-Agent": "tasco-maxspeed-inspector/0.1 (OSM enrichment; contact maps@tasco)"}
EDITS = Path(__file__).resolve().parent / "data" / "route_edits.json"
EDITS.parent.mkdir(exist_ok=True)

HAS = [0, 150, 60]      # green  — already has maxspeed (live or staged)
MISS = [200, 30, 30]    # red    — missing
SEL = [30, 90, 230]     # blue   — selected way

st.set_page_config(page_title="OSM Route Inspector", layout="wide")


# ----------------------------------------------------------------- data
@st.cache_data(ttl=600, show_spinner=False)
def fetch_route(ref):
    """Live Overpass: every member way of route=road relations with this ref in VN, + geometry."""
    q = f"""
[out:json][timeout:120];
area["ISO3166-1"="VN"][admin_level=2]->.vn;
relation(area.vn)["type"="route"]["route"="road"]["ref"="{ref}"]->.r;
.r out tags;
way(r.r);
out tags geom;
"""
    resp = requests.post(OVERPASS, data={"data": q}, headers=UA, timeout=150)
    resp.raise_for_status()
    rels, rows = [], []
    for e in resp.json()["elements"]:
        if e["type"] == "relation":
            rels.append(e["id"])
        elif e["type"] == "way" and "geometry" in e:
            t = e.get("tags", {})
            coords = [[round(p["lon"], 6), round(p["lat"], 6)] for p in e["geometry"]]
            if len(coords) < 2:
                continue
            km = GEOD.line_length([c[0] for c in coords], [c[1] for c in coords]) / 1000
            rows.append({
                "way_id": e["id"], "highway": t.get("highway", ""), "name": t.get("name", ""),
                "maxspeed": t.get("maxspeed", ""), "lanes": t.get("lanes", ""),
                "oneway": t.get("oneway", ""), "km": round(km, 3), "path": coords,
            })
    return pd.DataFrame(rows), sorted(set(rels))


def load_edits():
    return json.loads(EDITS.read_text()) if EDITS.exists() else {}


def save_edits(d):
    EDITS.write_text(json.dumps(d, ensure_ascii=False, indent=2))


def midpoint(path):
    return path[len(path) // 2]


def order_ways(df):
    """Route order via shared endpoint coords (clean-room: chain ways head-to-tail).

    Overpass `out geom` gives coords, not node ids, so we key on rounded first/last coords.
    Greedy walk per connected component, starting from a degree-1 endpoint where possible.
    Returns the way_id list in route order; disjoint pieces are appended after their walk.
    """
    from collections import defaultdict
    ends = {r.way_id: (tuple(r.path[0]), tuple(r.path[-1])) for r in df.itertuples()}
    touch = defaultdict(list)
    for wid, (a, b) in ends.items():
        touch[a].append(wid)
        touch[b].append(wid)

    def neighbors(wid):
        a, b = ends[wid]
        return [w for end in (a, b) for w in touch[end] if w != wid]

    remaining = set(ends)
    order = []
    while remaining:
        start = next((w for w in remaining
                      if len(touch[ends[w][0]]) == 1 or len(touch[ends[w][1]]) == 1),
                     next(iter(remaining)))
        cur = start
        while cur is not None and cur in remaining:
            order.append(cur)
            remaining.discard(cur)
            cur = next((w for w in neighbors(cur) if w in remaining), None)
    return order


# ----------------------------------------------------------------- page
st.title("🛣️ OSM Route Inspector + Maxspeed Editor")
st.caption("Live OSM route by ref → map + per-way maxspeed/lanes/median edit → staged to a local "
           "worklist. Apply in iD with street-view evidence. Nothing is written to OSM here.")

if "edits" not in st.session_state:
    st.session_state.edits = load_edits()
edits = st.session_state.edits

c = st.columns([2, 1, 3])
ref = c[0].text_input("Route ref", "QL.1", help="e.g. QL.1, QL.14, CT.01 — OSM relation ref tag")
go = c[1].button("Fetch live", type="primary")

if go or "df" in st.session_state:
    if go:
        try:
            with st.spinner(f"Overpass: fetching route {ref}…"):
                df, rel_ids = fetch_route(ref.strip())
            st.session_state.df = df
            st.session_state.rel_ids = rel_ids
            st.session_state.ref = ref.strip()
        except Exception as e:
            st.error(f"Overpass fetch failed: {e}")
            st.stop()
    df = st.session_state.df
    rel_ids = st.session_state.rel_ids
    ref = st.session_state.ref

    if df.empty:
        st.warning(f"No route=road relation with ref `{ref}` found in VN (try QL.1 / CT.01).")
        st.stop()

    # effective maxspeed = live tag OR a staged edit
    def eff_ms(r):
        e = edits.get(str(r["way_id"]), {})
        return e.get("maxspeed") or r["maxspeed"]

    df = df.copy()
    df["staged"] = df["way_id"].map(lambda w: str(w) in edits)
    df["eff_maxspeed"] = df.apply(eff_ms, axis=1)
    df["has_ms"] = df["eff_maxspeed"].astype(bool)

    # route order (head-to-tail) + cumulative km gutter, render.pl-style
    seq = order_ways(df)
    df = df.set_index("way_id").loc[seq].reset_index()
    df["cum_km"] = df["km"].cumsum().round(1)
    df["mid"] = df["path"].map(midpoint)
    df["M"] = df["mid"].map(lambda p: f"https://www.mapillary.com/app/?lat={p[1]}&lng={p[0]}&z=17")
    df["J"] = df.apply(lambda r: (
        "http://127.0.0.1:8111/load_and_zoom?"
        f"left={r['mid'][0]-0.01}&right={r['mid'][0]+0.01}"
        f"&top={r['mid'][1]+0.005}&bottom={r['mid'][1]-0.005}&select=way{r['way_id']}"), axis=1)
    df["L"] = df["way_id"].map(lambda w: f"http://level0.osmz.ru/?url=way/{w}!")

    rel_links = " · ".join(
        f"[{r}](https://www.openstreetmap.org/relation/{r})" for r in rel_ids)
    m = st.columns(5)
    m[0].metric("Member ways", f"{len(df):,}")
    m[1].metric("Total km", f"{df['km'].sum():,.1f}")
    m[2].metric("Has maxspeed", f"{100*df['has_ms'].mean():.0f}%")
    m[3].metric("Missing ways", f"{(~df['has_ms']).sum():,}")
    m[4].metric("Staged edits", f"{df['staged'].sum():,}")
    st.caption(f"Relations: {rel_links}  ·  ref `{ref}`")

    # ---- route-ordered way list (the strip) — doubles as the edit selector ----
    st.markdown("**Route strip — click a row to inspect / edit it** (top→tail, cumulative km)")
    strip = df.assign(
        ms=df.apply(lambda r: ("✎ " if r["staged"] else "") + (r["eff_maxspeed"] or "—"), axis=1),
    )[["cum_km", "way_id", "km", "name", "highway", "lanes", "ms", "M", "J", "L"]]
    event = st.dataframe(
        strip, hide_index=True, use_container_width=True, height=300,
        on_select="rerun", selection_mode="single-row",
        column_config={
            "cum_km": st.column_config.NumberColumn("km", format="%.1f", help="cumulative km"),
            "way_id": st.column_config.NumberColumn("Way", format="%d"),
            "km": st.column_config.NumberColumn("len", format="%.2f"),
            "name": "name", "highway": "hw", "lanes": "lanes",
            "ms": st.column_config.TextColumn("maxspeed", help="✎ = staged edit"),
            "M": st.column_config.LinkColumn("M", display_text="M", help="Mapillary"),
            "J": st.column_config.LinkColumn("J", display_text="J", help="JOSM remote control"),
            "L": st.column_config.LinkColumn("L", display_text="L", help="Level0 editor"),
        })
    rows_sel = event.selection.rows
    pick = rows_sel[0] if rows_sel else 0
    row = df.iloc[pick]

    # ---- map ----
    df["color"] = df.apply(
        lambda r: SEL if r["way_id"] == row["way_id"] else (HAS if r["has_ms"] else MISS), axis=1)
    df["width"] = df["way_id"].map(lambda w: 6 if w == row["way_id"] else 3)
    all_lons = [p[0] for path in df["path"] for p in path]
    all_lats = [p[1] for path in df["path"] for p in path]
    view = pdk.ViewState(longitude=sum(all_lons)/len(all_lons),
                         latitude=sum(all_lats)/len(all_lats), zoom=6)
    layer = pdk.Layer("PathLayer", df, get_path="path", get_color="color",
                      get_width="width", width_units="pixels", width_min_pixels=2, pickable=True)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view,
                             map_style="road",
                             tooltip={"text": "way {way_id}\n{name}\nms: {eff_maxspeed}"}),
                    use_container_width=True)
    st.caption("🟩 has maxspeed (live or staged) · 🟥 missing · 🟦 selected")

    # ---- edit panel ----
    wid = str(row["way_id"])
    lat, lon = midpoint(row["path"])[1], midpoint(row["path"])[0]
    st.subheader(f"Way {wid} — {row['name'] or row['highway']}")
    L, R = st.columns([1, 1])
    with L:
        st.markdown(
            f"**Current OSM:** maxspeed=`{row['maxspeed'] or '—'}` · lanes=`{row['lanes'] or '—'}` "
            f"· oneway=`{row['oneway'] or '—'}` · {row['km']:.2f} km")
        st.markdown(
            f"[🗺️ Mapillary](https://www.mapillary.com/app/?lat={lat}&lng={lon}&z=17) · "
            f"[📷 Street View](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}) · "
            f"[✏️ iD edit](https://www.openstreetmap.org/edit?way={wid}) · "
            f"[🔗 OSM way](https://www.openstreetmap.org/way/{wid})")
    with R:
        cur = edits.get(wid, {})
        with st.form("edit"):
            new_ms = st.text_input("maxspeed (km/h)", cur.get("maxspeed", row["maxspeed"]))
            new_lanes = st.text_input("lanes", cur.get("lanes", row["lanes"]))
            new_div = st.checkbox("dải phân cách giữa (physical median)",
                                  cur.get("divided", bool(row["oneway"])))
            note = st.text_input("evidence URL / note", cur.get("note", ""))
            cc = st.columns(2)
            if cc[0].form_submit_button("Stage edit", type="primary"):
                edits[wid] = {"ref": ref, "name": row["name"], "maxspeed": new_ms.strip(),
                              "lanes": new_lanes.strip(), "divided": new_div, "note": note.strip()}
                save_edits(edits)
                st.success("Staged.")
                st.rerun()
            if cc[1].form_submit_button("Remove from worklist") and wid in edits:
                del edits[wid]
                save_edits(edits)
                st.rerun()

    # ---- worklist ----
    if edits:
        st.subheader(f"📝 Staged worklist ({len(edits)})")
        wl = pd.DataFrame([{"way_id": k, **v} for k, v in edits.items()])
        st.dataframe(wl, hide_index=True, use_container_width=True)
        d = st.columns(2)
        d[0].download_button("⬇️ Download worklist JSON",
                             json.dumps(edits, ensure_ascii=False, indent=2),
                             file_name=f"route_edits_{ref}.json", mime="application/json")
        if d[1].button("Clear worklist"):
            st.session_state.edits = {}
            save_edits({})
            st.rerun()
else:
    st.info("Enter a route ref (e.g. QL.1) and click **Fetch live**.")
