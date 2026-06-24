"""
upload.py — Upload COGs to Cloudflare R2 (or S3) and update STAC catalog.

Usage:
    python upload.py \
        --input ./cogs \
        --bucket tasco-imagery-hanoi \
        --source sentinel2
"""

import argparse
import json
import os
from pathlib import Path

import boto3
from botocore.config import Config


def get_r2_client(endpoint: str = None, access_key: str = None, secret_key: str = None):
    """Create an S3-compatible client for Cloudflare R2."""
    endpoint = endpoint or os.environ.get("R2_ENDPOINT", "")
    access_key = access_key or os.environ.get("R2_ACCESS_KEY", "")
    secret_key = secret_key or os.environ.get("R2_SECRET_KEY", "")

    if not endpoint:
        raise ValueError("R2_ENDPOINT required (e.g. https://<account_id>.r2.cloudflarestorage.com)")

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def get_s3_client(region: str = "ap-southeast-1"):
    """Create a standard AWS S3 client."""
    return boto3.client("s3", region_name=region)


def upload_cog(client, bucket: str, local_path: Path, remote_key: str):
    """Upload a COG file to the bucket."""
    size_mb = local_path.stat().st_size / (1024 * 1024)
    print(f"  Uploading {local_path.name} ({size_mb:.1f} MB) -> s3://{bucket}/{remote_key}")

    client.upload_file(
        str(local_path),
        bucket,
        remote_key,
        ExtraArgs={"ContentType": "image/tiff"},
    )


def upload_catalog(client, bucket: str, catalog: dict):
    """Upload the STAC catalog JSON."""
    body = json.dumps(catalog, indent=2).encode()
    client.put_object(
        Bucket=bucket,
        Key="stac/catalog.json",
        Body=body,
        ContentType="application/json",
    )
    print(f"  Catalog uploaded: s3://{bucket}/stac/catalog.json")


def build_catalog(bucket: str, source: str, cogs: list, server_url: str) -> dict:
    """Build or update the STAC catalog JSON."""
    catalog = {
        "type": "Catalog",
        "id": f"tasco-imagery-{bucket}",
        "description": "TASCO timeseries satellite imagery",
        "stac_version": "1.0.0",
        "sources": {},
    }

    # Try to fetch existing catalog
    # (In production, download existing catalog.json and merge)

    entries = []
    for cog in cogs:
        date = cog["date"]
        remote_key = f"{source}/{date}/composite.tif"
        tile_url = f"{server_url}/{source}/{date}/tiles/{{z}}/{{x}}/{{y}}.png"

        entries.append({
            "date": date,
            "href": tile_url,
            "cog_key": remote_key,
        })

    catalog["sources"][source] = entries
    return catalog


def main():
    parser = argparse.ArgumentParser(description="Upload COGs to R2/S3")
    parser.add_argument("--input", required=True, help="COGs directory (with processed.json)")
    parser.add_argument("--bucket", required=True, help="R2/S3 bucket name")
    parser.add_argument("--source", default="sentinel2", help="Source name (sentinel2, planet, etc)")
    parser.add_argument("--storage", choices=["r2", "s3"], default="r2", help="Storage backend")
    parser.add_argument("--server-url", default="https://tiles.tasco-internal.vn",
                        help="Tile server base URL for catalog")
    args = parser.parse_args()

    input_dir = Path(args.input)

    # Read processing manifest
    manifest_path = input_dir / "processed.json"
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found. Run process.py first.")
        return

    manifest = json.loads(manifest_path.read_text())
    cogs = manifest.get("cogs", [])

    if not cogs:
        print("No COGs to upload.")
        return

    # Create client
    if args.storage == "r2":
        client = get_r2_client()
    else:
        client = get_s3_client()

    print(f"Uploading {len(cogs)} COGs to {args.storage}://{args.bucket}/")

    # Upload COGs
    for cog in cogs:
        local_path = Path(cog["path"])
        if not local_path.exists():
            print(f"  SKIP: {local_path} not found")
            continue

        remote_key = f"{args.source}/{cog['date']}/composite.tif"
        upload_cog(client, args.bucket, local_path, remote_key)

    # Build and upload catalog
    catalog = build_catalog(args.bucket, args.source, cogs, args.server_url)
    upload_catalog(client, args.bucket, catalog)

    print(f"\nDone. {len(cogs)} COGs uploaded, catalog updated.")


if __name__ == "__main__":
    main()
