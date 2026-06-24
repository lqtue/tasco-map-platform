#!/usr/bin/env bash
# Baseline: % of Vietnam's tertiary+ road km that carry a maxspeed tag in OSM.
# Requires: osmium (osmium-tool), python3 + pyproj. ~250 MB download, runs in a few min.
set -euo pipefail
cd "$(dirname "$0")"

PBF="vietnam-latest.osm.pbf"
URL="https://download.geofabrik.de/asia/vietnam-latest.osm.pbf"
FILTERED="vn-major.osm.pbf"

if [ ! -f "$PBF" ]; then
  echo ">> downloading $URL"
  curl -L --fail -o "$PBF" "$URL"
fi
echo ">> extract date: $(osmium fileinfo -e -g header.option.timestamp "$PBF" 2>/dev/null || true)"

echo ">> filtering tertiary+ highways"
osmium tags-filter -o "$FILTERED" --overwrite "$PBF" \
  w/highway=motorway,trunk,primary,secondary,tertiary,motorway_link,trunk_link,primary_link,secondary_link,tertiary_link

echo ">> exporting geometries + tallying"
osmium export "$FILTERED" -f geojsonseq --geometry-types=linestring \
  | python3 maxspeed_coverage.py
