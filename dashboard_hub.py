"""One entry point for every Streamlit dashboard in the repo.

Native multipage nav — each existing app runs unchanged as a page (it keeps
its own __file__, data paths, caching, and set_page_config). No merging of
internals; this is just a router so it's one port / one sidebar instead of
launching three streamlit processes by hand.

Run: archive/admin-poi/coverage/.venv/bin/python -m streamlit run dashboard_hub.py

ponytail: launcher does NOT call st.set_page_config — each page sets its own,
and set_page_config may only be called once per run.
"""
import streamlit as st

st.navigation({
    "Overview": [
        st.Page("archive/dashboards/app.py", url_path="multi",
                title="Multi-product (all criteria)", default=True),
    ],
    "Maxspeed (live work)": [
        st.Page("traffic/maxspeed/dashboard/app_maxspeed.py", url_path="maxspeed",
                title="Maxspeed — cell map"),
        st.Page("traffic/maxspeed/dashboard/app_inspect.py", url_path="inspect",
                title="Maxspeed — route inspector / editor"),
    ],
    "Buy planning": [
        st.Page("archive/admin-poi/coverage/dashboard/app.py", url_path="coverage",
                title="Coverage — sat buy-envelope"),
        st.Page("archive/admin-poi/coverage/dashboard/app_poi.py", url_path="poi",
                title="POI — AWS resolution sizing"),
    ],
}).run()
