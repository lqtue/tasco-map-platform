#!/usr/bin/env python3
"""Local SQLite search index — way id / relation id / ref / name -> geometry+tags.

Lets the web app search offline instead of hitting Overpass. Run once (or after
re-filtering the PBFs):

  .venv/bin/python3 data/build_index.py        (from the explore/ dir)

Reads config.ROADS_PBF / config.RELS_PBF, writes config.SQLITE.
"""
import json
import sqlite3
import sys
from pathlib import Path

import osmium

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import config


def main():
    db = config.SQLITE
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE way (id INTEGER PRIMARY KEY, version INTEGER, tags TEXT, geom TEXT, node_ids TEXT)"
    )
    con.execute("CREATE TABLE relation (id INTEGER PRIMARY KEY, ref TEXT, name TEXT, tags TEXT)")
    con.execute("CREATE TABLE rel_member (rel_id INTEGER, way_id INTEGER)")

    # ways: id -> version, tags, [[lat,lon],...], [node_id,...] (node_ids needed to build a
    # valid osmChange <modify> element later — the way's nd refs must be its *unchanged*
    # original list, not something we can reconstruct from coordinates alone).
    # roads.osm.pbf = tertiary+ filter, see extract commands in README.md.
    fp = osmium.FileProcessor(str(config.ROADS_PBF)).with_locations()
    n = 0
    for o in fp:
        if not o.is_way():
            continue
        coords = [[nd.lat, nd.lon] for nd in o.nodes if nd.location.valid()]
        if len(coords) < 2:
            continue
        node_ids = [nd.ref for nd in o.nodes]
        con.execute(
            "INSERT OR REPLACE INTO way VALUES (?,?,?,?,?)",
            (o.id, o.version, json.dumps(dict(o.tags)), json.dumps(coords), json.dumps(node_ids)),
        )
        n += 1
    print(f"{n:,} ways indexed")

    # route relations: id -> ref/name + member way ids (routerels.osm.pbf = r/type=route filter)
    fp = osmium.FileProcessor(str(config.RELS_PBF)).with_filter(
        osmium.filter.EntityFilter(osmium.osm.RELATION)
    )
    m = 0
    for o in fp:
        t = o.tags
        if t.get("type") != "route" or t.get("route") != "road":
            continue
        con.execute(
            "INSERT OR REPLACE INTO relation VALUES (?,?,?,?)",
            (o.id, t.get("ref"), t.get("name"), json.dumps(dict(t))),
        )
        for mem in o.members:
            if mem.type == "w":
                con.execute("INSERT INTO rel_member VALUES (?,?)", (o.id, mem.ref))
        m += 1
    print(f"{m:,} route relations indexed")

    con.execute("CREATE INDEX idx_rel_ref ON relation(ref)")
    con.execute("CREATE INDEX idx_rel_name ON relation(name)")
    con.execute("CREATE INDEX idx_member_rel ON rel_member(rel_id)")
    con.commit()
    con.close()
    print(f"wrote {db} ({db.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
