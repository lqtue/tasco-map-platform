"""Render the sign pipeline as an inspectable map (no trust-the-number needed).

For a route's triangulated signs it draws, per sign:
  • the member detections (camera dots) + their bearing rays — you can see the
    rays from different frames converge on the sign (the triangulation),
  • the triangulated sign marker, coloured by its verdict vs OSM,
  • a dashed connector to the nearest OSM segment — how the sign "points to" the
    road it was matched to,
plus the route's OSM ways (grey, maxspeed in the tooltip).

Reads the artefacts compare_osm.py already wrote (no network). Output is a
single self-contained HTML (Leaflet from CDN).

Usage:  python3 traffic/signs/inspect_map.py   # writes + prints the html path
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
VERDICT_COLOR = {
    "agree": "#16a34a",
    "disagree_osm_stale": "#dc2626",
    "disagree_check": "#f59e0b",
    "osm_missing": "#2563eb",
    "off_route": "#9ca3af",
}


def _nearest_on_ways(lon, lat, ways):
    """Closest point on any OSM way (for the connector line). Local-meter approx."""
    mlat = 111320.0
    mlon = 111320.0 * math.cos(math.radians(lat))
    best, bd = None, math.inf
    for w in ways:
        line = w["line"]
        for (x1, y1), (x2, y2) in zip(line, line[1:]):
            ax, ay = (x1 - lon) * mlon, (y1 - lat) * mlat
            bx, by = (x2 - lon) * mlon, (y2 - lat) * mlat
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / L2))
            px, py = ax + t * dx, ay + t * dy
            d = math.hypot(px, py)
            if d < bd:
                bd = d
                best = (lon + px / mlon, lat + py / mlat, w.get("maxspeed"), w["id"])
    return best


def _ray_end(lon, lat, bearing_deg, dist_m):
    """Endpoint of a bearing ray of length dist_m from (lon,lat)."""
    b = math.radians(bearing_deg)
    dlat = (dist_m * math.cos(b)) / 111320.0
    dlon = (dist_m * math.sin(b)) / (111320.0 * math.cos(math.radians(lat)))
    return [lon + dlon, lat + dlat]


def build(ref="QL.51"):
    signs = pd.read_parquet(DATA / "ql51_signs.parquet")
    obs = pd.read_parquet(DATA / "ql51_observations.parquet")
    ways = json.loads((DATA / "QL_51_ways.json").read_text())
    members = {k: g for k, g in obs.groupby("map_feature_id")}

    sign_features = []
    for s in signs.itertuples():
        on_route = s.dist_road_m <= 30
        rays, cams = [], []
        if on_route:
            g = members.get(s.map_feature_id)
            if g is not None:
                for d in g.itertuples():
                    dist = max(8.0, math.dist((s.lon, s.lat), (d.lon, d.lat)) * 111320.0)
                    cams.append([d.lon, d.lat])
                    rays.append([[d.lon, d.lat], _ray_end(d.lon, d.lat, d.bearing_deg, dist)])
        near = _nearest_on_ways(s.lon, s.lat, ways) if on_route else None
        sign_features.append({
            "lon": s.lon, "lat": s.lat, "value": s.value, "verdict": s.verdict,
            "n_views": int(s.n_views), "spread": round(float(s.ray_spread_m), 2),
            "osm": s.osm_maxspeed, "dist": round(float(s.dist_road_m), 1),
            "seen": s.sign_obs_date, "osm_set": s.osm_edit_date,
            "color": VERDICT_COLOR.get(s.verdict, "#000"),
            "cams": cams, "rays": rays,
            "connector": [[s.lon, s.lat], [near[0], near[1]]] if near else None,
        })

    osm_lines = [{"line": w["line"], "ms": w.get("maxspeed"), "id": w["id"]} for w in ways]
    html = _TEMPLATE.replace("__REF__", ref) \
        .replace("__SIGNS__", json.dumps(sign_features)) \
        .replace("__OSM__", json.dumps(osm_lines)) \
        .replace("__COLORS__", json.dumps(VERDICT_COLOR))
    out = DATA / "ql51_inspect.html"
    out.write_text(html)
    n_on = sum(1 for f in sign_features if f["dist"] <= 30)
    print(f"wrote {out}  ({len(sign_features)} signs, {n_on} on-route)")
    return out


_TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<title>__REF__ sign triangulation → OSM</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
 html,body,#map{height:100%;margin:0}
 .legend{background:#fff;padding:8px 10px;font:12px sans-serif;line-height:1.6;box-shadow:0 1px 4px rgba(0,0,0,.3);border-radius:5px}
 .sw{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px;vertical-align:middle}
 .pin{font:700 11px sans-serif;color:#fff;text-align:center;text-shadow:0 0 2px #000}
</style></head><body><div id="map"></div><script>
const SIGNS=__SIGNS__, OSM=__OSM__, COLORS=__COLORS__;
const map=L.map('map');
L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',{maxZoom:21,attribution:'Imagery © Google'}).addTo(map);
// OSM ways (grey) with maxspeed tooltip
OSM.forEach(w=>{const ll=w.line.map(c=>[c[1],c[0]]);
  L.polyline(ll,{color:'#1f2937',weight:2,opacity:.5}).bindTooltip('way '+w.id+' · maxspeed '+(w.ms||'—')).addTo(map);});
const all=[];
SIGNS.forEach(s=>{
  // rays from each camera converging on the sign
  s.rays.forEach(r=>L.polyline(r.map(c=>[c[1],c[0]]),{color:s.color,weight:1,opacity:.5}).addTo(map));
  s.cams.forEach(c=>L.circleMarker([c[1],c[0]],{radius:2,color:s.color,fillOpacity:.7,weight:0}).addTo(map));
  // dashed connector to the matched OSM segment
  if(s.connector)L.polyline(s.connector.map(c=>[c[1],c[0]]),{color:s.color,weight:2,dashArray:'4,4'}).addTo(map);
  // the triangulated sign
  const m=L.circleMarker([s.lat,s.lon],{radius:Math.min(6+s.n_views,16),color:'#111',weight:1,fillColor:s.color,fillOpacity:.9}).addTo(map);
  m.bindPopup('<b>sign '+s.value+' km/h</b> · '+s.verdict+'<br>'
    +'views (deduped): '+s.n_views+' · ray spread '+s.spread+' m<br>'
    +'matched OSM maxspeed: '+s.osm+' · '+s.dist+' m off road<br>'
    +'sign seen '+s.seen+' · OSM maxspeed set '+s.osm_set);
  L.marker([s.lat,s.lon],{icon:L.divIcon({className:'',html:'<div class="pin">'+s.value+'</div>',iconSize:[24,14],iconAnchor:[12,7]})}).addTo(map);
  if(s.dist<=30)all.push([s.lat,s.lon]);
});
map.fitBounds(all.length?all:OSM.flatMap(w=>w.line.map(c=>[c[1],c[0]])));
// legend
const lg=L.control({position:'topright'});
lg.onAdd=()=>{const d=L.DomUtil.create('div','legend');d.innerHTML='<b>__REF__ — sign → OSM</b><br>'
  +Object.entries(COLORS).map(([k,v])=>'<span class="sw" style="background:'+v+'"></span>'+k).join('<br>')
  +'<hr style="margin:5px 0">dot=detection · ray=bearing · dash=match to OSM<br>marker size = #views';return d;};
lg.addTo(map);
</script></body></html>"""


if __name__ == "__main__":
    build()
