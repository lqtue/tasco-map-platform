"""
acquire.py — Search and download HLS scenes from NASA CMR/Earthdata.

Usage:
    python acquire.py \
        --aoi 105.75,20.95,105.90,21.10 \
        --start 2025-01 \
        --end 2025-06 \
        --max-cloud 20 \
        --output ./downloads
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode


CMR_SEARCH_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
HLS_L30_COLLECTION = "C2021957657-LPCLOUD"  # HLS Landsat 30m
HLS_S30_COLLECTION = "C2021957295-LPCLOUD"  # HLS Sentinel-2 30m
STAC_SEARCH_URL = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD/search"


def parse_aoi(aoi_str: str) -> dict:
    """Parse 'west,south,east,north' into a bbox dict."""
    parts = [float(x.strip()) for x in aoi_str.split(",")]
    if len(parts) != 4:
        raise ValueError("AOI must be west,south,east,north")
    return {"west": parts[0], "south": parts[1], "east": parts[2], "north": parts[3]}


def search_hls_stac(bbox: dict, start: str, end: str, max_cloud: int,
                     collection: str = HLS_S30_COLLECTION, limit: int = 100) -> list:
    """Search HLS via CMR STAC API."""
    body = {
        "collections": [collection],
        "bbox": [bbox["west"], bbox["south"], bbox["east"], bbox["north"]],
        "datetime": f"{start}-01T00:00:00Z/{end}-28T23:59:59Z",
        "limit": limit,
        "query": {
            "eo:cloud_cover": {"lte": max_cloud}
        },
    }

    req = Request(
        STAC_SEARCH_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    print(f"Searching CMR STAC: {collection}")
    print(f"  AOI: {bbox}")
    print(f"  Date range: {start} to {end}")
    print(f"  Max cloud cover: {max_cloud}%")

    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    features = data.get("features", [])
    print(f"  Found {len(features)} granules")
    return features


def search_hls_cmr(bbox: dict, start: str, end: str, max_cloud: int,
                    collection: str = HLS_S30_COLLECTION, page_size: int = 100) -> list:
    """Search HLS via CMR JSON API (fallback)."""
    params = {
        "collection_concept_id": collection,
        "bounding_box": f"{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}",
        "temporal": f"{start}-01T00:00:00Z,{end}-28T23:59:59Z",
        "cloud_cover": f"0,{max_cloud}",
        "page_size": page_size,
        "sort_key": "-start_date",
    }

    url = f"{CMR_SEARCH_URL}?{urlencode(params)}"
    req = Request(url, headers={"Accept": "application/json"})

    print(f"Searching CMR: {collection}")
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    entries = data.get("feed", {}).get("entry", [])
    print(f"  Found {len(entries)} granules")
    return entries


def select_best_per_month(features: list) -> dict:
    """Group scenes by month, pick lowest cloud cover per month."""
    monthly = {}
    for f in features:
        props = f.get("properties", f)
        dt_str = props.get("datetime", props.get("time_start", ""))[:7]  # YYYY-MM
        cloud = props.get("eo:cloud_cover", props.get("cloud_cover", 100))

        if dt_str not in monthly or cloud < monthly[dt_str]["cloud_cover"]:
            monthly[dt_str] = {
                "id": f.get("id", props.get("id", "")),
                "datetime": dt_str,
                "cloud_cover": cloud,
                "feature": f,
            }

    print(f"\nBest scene per month ({len(monthly)} months):")
    for month in sorted(monthly.keys()):
        entry = monthly[month]
        print(f"  {month}: cloud={entry['cloud_cover']:.1f}%  id={entry['id']}")

    return monthly


def get_download_links(feature: dict) -> list:
    """Extract COG download URLs from a STAC feature."""
    assets = feature.get("assets", {})
    links = []

    # HLS band assets are named B01, B02, ... or by band name
    rgb_bands = ["B04", "B03", "B02"]  # Red, Green, Blue for true color
    tci_key = "browse"  # Some collections have a browse/TCI asset

    for band in rgb_bands:
        if band in assets:
            links.append({
                "band": band,
                "href": assets[band].get("href", ""),
                "type": assets[band].get("type", ""),
            })

    # Also grab Fmask for cloud masking
    if "Fmask" in assets:
        links.append({
            "band": "Fmask",
            "href": assets["Fmask"].get("href", ""),
            "type": assets["Fmask"].get("type", ""),
        })

    # Fallback: grab all GeoTIFF assets
    if not links:
        for key, asset in assets.items():
            if asset.get("type", "").startswith("image/tiff"):
                links.append({
                    "band": key,
                    "href": asset.get("href", ""),
                    "type": asset.get("type", ""),
                })

    return links


def download_scene(links: list, output_dir: Path, scene_id: str, token: str = None):
    """Download band files for a scene."""
    scene_dir = output_dir / scene_id
    scene_dir.mkdir(parents=True, exist_ok=True)

    headers = {"Accept": "*/*"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for link in links:
        filename = f"{link['band']}.tif"
        filepath = scene_dir / filename

        if filepath.exists():
            print(f"  Skipping (exists): {filename}")
            continue

        print(f"  Downloading: {link['band']} -> {filepath}")
        try:
            req = Request(link["href"], headers=headers)
            with urlopen(req, timeout=120) as resp:
                filepath.write_bytes(resp.read())
        except Exception as e:
            print(f"  ERROR downloading {link['band']}: {e}")
            # NASA Earthdata requires .netrc auth for actual downloads
            # See: https://urs.earthdata.nasa.gov/
            if "401" in str(e) or "403" in str(e):
                print("  → You need a NASA Earthdata token. Set --token or configure ~/.netrc")
                print("  → Register at: https://urs.earthdata.nasa.gov/users/new")
                print("  → Then: echo 'machine urs.earthdata.nasa.gov login USER password PASS' >> ~/.netrc")
                return False

    return True


def save_search_results(monthly: dict, output_dir: Path):
    """Save search results as JSON for the process step."""
    manifest = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "scenes": {},
    }
    for month, entry in sorted(monthly.items()):
        links = get_download_links(entry["feature"])
        manifest["scenes"][month] = {
            "id": entry["id"],
            "datetime": entry["datetime"],
            "cloud_cover": entry["cloud_cover"],
            "links": links,
        }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest saved: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(description="Search and download HLS scenes from NASA CMR")
    parser.add_argument("--aoi", required=True, help="Bounding box: west,south,east,north")
    parser.add_argument("--start", required=True, help="Start month: YYYY-MM")
    parser.add_argument("--end", required=True, help="End month: YYYY-MM")
    parser.add_argument("--max-cloud", type=int, default=20, help="Max cloud cover %% (default: 20)")
    parser.add_argument("--output", default="./downloads", help="Output directory")
    parser.add_argument("--collection", choices=["S30", "L30", "both"], default="S30",
                        help="HLS collection: S30 (Sentinel-2), L30 (Landsat), both")
    parser.add_argument("--token", default=None, help="NASA Earthdata Bearer token")
    parser.add_argument("--search-only", action="store_true", help="Search only, don't download")
    args = parser.parse_args()

    bbox = parse_aoi(args.aoi)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Search
    collections = []
    if args.collection in ("S30", "both"):
        collections.append(("HLS-S30", HLS_S30_COLLECTION))
    if args.collection in ("L30", "both"):
        collections.append(("HLS-L30", HLS_L30_COLLECTION))

    all_features = []
    for name, cid in collections:
        try:
            features = search_hls_stac(bbox, args.start, args.end, args.max_cloud, cid)
            all_features.extend(features)
        except Exception as e:
            print(f"  STAC search failed ({e}), trying CMR JSON...")
            entries = search_hls_cmr(bbox, args.start, args.end, args.max_cloud, cid)
            all_features.extend(entries)

    if not all_features:
        print("No scenes found. Try increasing --max-cloud or widening the date range.")
        sys.exit(1)

    monthly = select_best_per_month(all_features)
    save_search_results(monthly, output_dir)

    if args.search_only:
        print("\n--search-only: skipping downloads.")
        return

    # Download
    print(f"\nDownloading {len(monthly)} scenes to {output_dir}/")
    for month, entry in sorted(monthly.items()):
        links = get_download_links(entry["feature"])
        if links:
            print(f"\n{month} ({entry['id']}):")
            success = download_scene(links, output_dir, entry["id"], args.token)
            if not success:
                print("Download auth failed. Run with --search-only first, then configure auth.")
                break
        else:
            print(f"\n{month}: no downloadable assets found for {entry['id']}")


if __name__ == "__main__":
    main()
