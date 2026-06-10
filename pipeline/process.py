"""
process.py — Process downloaded HLS scenes into analysis-ready COGs.

Takes raw HLS band files, applies cloud masking (Fmask), clips to AOI,
composites RGB, and outputs Cloud-Optimized GeoTIFFs.

Usage:
    python process.py \
        --input ./downloads \
        --output ./cogs \
        --aoi 105.75,20.95,105.90,21.10
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.windows import from_bounds as window_from_bounds
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles


# Hanoi AOI default
DEFAULT_AOI = "105.75,20.95,105.90,21.10"
TARGET_CRS = CRS.from_epsg(3857)  # Web Mercator for tile serving


def parse_aoi(aoi_str: str) -> tuple:
    parts = [float(x.strip()) for x in aoi_str.split(",")]
    return parts[0], parts[1], parts[2], parts[3]  # west, south, east, north


def apply_cloud_mask(rgb_data: np.ndarray, fmask_path: Path) -> np.ndarray:
    """Apply Fmask cloud/shadow mask to RGB data. Masked pixels become nodata (0)."""
    if not fmask_path.exists():
        print("    No Fmask found, skipping cloud masking")
        return rgb_data

    with rasterio.open(fmask_path) as fm:
        fmask = fm.read(1)

    # HLS Fmask bit values:
    # Bit 1: Cloud, Bit 2: Adjacent cloud shadow, Bit 3: Cloud shadow
    # Mask where any cloud/shadow bit is set
    cloud_mask = (fmask & 0b1110) > 0

    # Expand mask to match RGB shape (3, H, W)
    for band in range(rgb_data.shape[0]):
        rgb_data[band][cloud_mask] = 0

    masked_pct = (cloud_mask.sum() / cloud_mask.size) * 100
    print(f"    Cloud mask applied: {masked_pct:.1f}% pixels masked")
    return rgb_data


def composite_rgb(scene_dir: Path, fmask: bool = True) -> tuple:
    """Read B04 (Red), B03 (Green), B02 (Blue) and composite into RGB array."""
    band_files = {}
    for band_name in ["B04", "B03", "B02", "Fmask"]:
        p = scene_dir / f"{band_name}.tif"
        if p.exists():
            band_files[band_name] = p

    if not all(b in band_files for b in ["B04", "B03", "B02"]):
        raise FileNotFoundError(f"Missing RGB bands in {scene_dir}")

    # Read bands
    bands = []
    profile = None
    for band_name in ["B04", "B03", "B02"]:
        with rasterio.open(band_files[band_name]) as src:
            bands.append(src.read(1))
            if profile is None:
                profile = src.profile.copy()

    rgb = np.stack(bands, axis=0)  # (3, H, W)

    # Apply cloud mask
    if fmask and "Fmask" in band_files:
        rgb = apply_cloud_mask(rgb, band_files["Fmask"])

    return rgb, profile


def clip_and_reproject(data: np.ndarray, src_profile: dict,
                       aoi: tuple, target_crs: CRS) -> tuple:
    """Clip to AOI bounding box and reproject to target CRS."""
    west, south, east, north = aoi

    # Calculate output transform and dimensions
    src_crs = src_profile["crs"]
    src_transform = src_profile["transform"]
    src_height, src_width = data.shape[1], data.shape[2]

    dst_transform, dst_width, dst_height = calculate_default_transform(
        src_crs, target_crs,
        src_width, src_height,
        left=west, bottom=south, right=east, top=north,
    )

    dst_data = np.zeros((data.shape[0], dst_height, dst_width), dtype=data.dtype)

    for band in range(data.shape[0]):
        reproject(
            source=data[band],
            destination=dst_data[band],
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=target_crs,
            resampling=Resampling.bilinear,
        )

    dst_profile = src_profile.copy()
    dst_profile.update({
        "crs": target_crs,
        "transform": dst_transform,
        "width": dst_width,
        "height": dst_height,
        "count": data.shape[0],
    })

    return dst_data, dst_profile


def write_cog(data: np.ndarray, profile: dict, output_path: Path):
    """Write data as a Cloud-Optimized GeoTIFF."""
    tmp_path = output_path.with_suffix(".tmp.tif")

    profile.update({
        "driver": "GTiff",
        "count": data.shape[0],
        "dtype": data.dtype,
        "nodata": 0,
    })

    with rasterio.open(tmp_path, "w", **profile) as dst:
        dst.write(data)

    # Convert to COG
    cog_profile = cog_profiles.get("deflate")
    cog_translate(
        tmp_path,
        output_path,
        cog_profile,
        in_memory=True,
        quiet=True,
    )

    tmp_path.unlink(missing_ok=True)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    COG written: {output_path} ({size_mb:.1f} MB)")


def process_scene(scene_dir: Path, output_dir: Path, aoi: tuple, date_label: str):
    """Process a single scene directory into a COG."""
    print(f"\n  Processing: {scene_dir.name} -> {date_label}")

    try:
        rgb, profile = composite_rgb(scene_dir)
    except FileNotFoundError as e:
        print(f"    SKIP: {e}")
        return None

    clipped, clipped_profile = clip_and_reproject(rgb, profile, aoi, TARGET_CRS)

    output_path = output_dir / f"{date_label}.tif"
    write_cog(clipped, clipped_profile, output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Process HLS scenes into COGs")
    parser.add_argument("--input", required=True, help="Downloads directory (with manifest.json)")
    parser.add_argument("--output", default="./cogs", help="Output directory for COGs")
    parser.add_argument("--aoi", default=DEFAULT_AOI, help="Bounding box: west,south,east,north")
    parser.add_argument("--no-cloud-mask", action="store_true", help="Skip cloud masking")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    aoi = parse_aoi(args.aoi)

    # Read manifest
    manifest_path = input_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        scenes = manifest.get("scenes", {})
    else:
        # No manifest — process all subdirectories
        scenes = {}
        for d in sorted(input_dir.iterdir()):
            if d.is_dir():
                scenes[d.name] = {"id": d.name, "datetime": d.name}

    print(f"Processing {len(scenes)} scenes")
    print(f"AOI: {aoi}")
    print(f"Output: {output_dir}")

    results = []
    for month, meta in sorted(scenes.items()):
        scene_id = meta.get("id", month)
        scene_dir = input_dir / scene_id
        if not scene_dir.exists():
            print(f"\n  SKIP: {scene_dir} not found")
            continue

        cog_path = process_scene(scene_dir, output_dir, aoi, month)
        if cog_path:
            results.append({"date": month, "path": str(cog_path)})

    # Save processing manifest
    proc_manifest = output_dir / "processed.json"
    proc_manifest.write_text(json.dumps({"cogs": results}, indent=2))
    print(f"\n{len(results)} COGs generated. Manifest: {proc_manifest}")


if __name__ == "__main__":
    main()
