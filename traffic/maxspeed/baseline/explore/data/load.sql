-- Run from the explore/ dir (CSVs land there):  psql -d tasco_geo -f data/load.sql
CREATE TEMP TABLE way_stage (id BIGINT, version BIGINT, tags TEXT, wkt TEXT, node_ids TEXT);
\copy way_stage FROM 'way_stage.csv' CSV
TRUNCATE way CASCADE;
INSERT INTO way (id, version, tags, geom, node_ids)
  SELECT id, version, tags::jsonb, ST_GeomFromText(wkt, 4326), node_ids::jsonb FROM way_stage;

TRUNCATE relation CASCADE;
\copy relation FROM 'relation.csv' CSV
TRUNCATE rel_member;
\copy rel_member FROM 'rel_member.csv' CSV

CREATE INDEX IF NOT EXISTS idx_way_geom ON way USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_relation_ref ON relation (ref);
CREATE INDEX IF NOT EXISTS idx_relation_name ON relation (name);
CREATE INDEX IF NOT EXISTS idx_rel_member_rel ON rel_member (rel_id);

SELECT 'way' t, count(*) FROM way
UNION ALL SELECT 'relation', count(*) FROM relation
UNION ALL SELECT 'rel_member', count(*) FROM rel_member;
