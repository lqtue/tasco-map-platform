#!/usr/bin/env python3
"""Shared helpers for the maxspeed baseline tally scripts.

Geodesic (WGS84) length, the tertiary+ class set, and the GeoJSONSeq stdin
reader that every coverage script otherwise repeats verbatim. Importable
because Python puts a script's own directory on sys.path[0], so
`python3 traffic/maxspeed/baseline/maxspeed_coverage.py` (run from the repo
root) still resolves `import geo`.
"""
import json
import re

from pyproj import Geod

GEOD = Geod(ellps="WGS84")

# "tertiary trở lên" — main hierarchy, highest → lowest importance.
MAIN_CLASSES = ["motorway", "trunk", "primary", "secondary", "tertiary"]


def base_class(hw):
    """Fold a `_link` class into its parent; pass everything else through."""
    return hw[:-5] if hw and hw.endswith("_link") else hw


def is_oneway(tags, hw=None):
    """Divided carriageway: explicit oneway tag, or motorway (oneway by OSM default)."""
    return tags.get("oneway") in ("yes", "-1", "true", "1") or hw == "motorway"


def line_len_m(coords):
    if len(coords) < 2:
        return 0.0
    return GEOD.line_length([c[0] for c in coords], [c[1] for c in coords])


def feature_len_m(geom):
    t = geom.get("type")
    c = geom.get("coordinates") or []
    if t == "LineString":
        return line_len_m(c)
    if t == "MultiLineString":
        return sum(line_len_m(p) for p in c)
    return 0.0


def iter_geojsonseq(stream):
    """Yield (props, geometry) for each feature line of an
    `osmium export -f geojsonseq` stream (RS-delimited or plain newline)."""
    for line in stream:
        line = line.strip("\x1e \t\r\n")
        if not line or line[0] != "{":
            continue
        feat = json.loads(line)
        yield feat.get("properties") or {}, feat.get("geometry") or {}


def km(x):
    return x / 1000.0


def pct(a, b):
    return (100.0 * a / b) if b else 0.0


_NUM = re.compile(r"\d+")


def ms_code(val):
    """maxspeed tag value -> int km/h, 0 = absent, -1 = present but non-numeric."""
    if not val:
        return 0
    m = _NUM.search(val)
    return int(m.group()) if m else -1


def iter_road_routes(pbf):
    """Yield (ref, relation) for every `type=route, route=road` relation carrying a
    ref (or `name` used as ref) — the relation walk the route_* scripts share.
    osmium is imported lazily so the geojsonseq tally scripts need only pyproj."""
    import osmium

    fp = osmium.FileProcessor(pbf).with_filter(
        osmium.filter.EntityFilter(osmium.osm.RELATION))
    for o in fp:
        t = o.tags
        if t.get("type") == "route" and t.get("route") == "road":
            ref = t.get("ref") or t.get("name")
            if ref:
                yield ref, o
