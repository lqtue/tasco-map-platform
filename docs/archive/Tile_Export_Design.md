# Tile Export Design — Fork the NASA Earthdata Plugin

**Status:** Draft  
**Replaces:** custom `pipeline/acquire.py` + `process.py` + `upload.py`  
**Keeps:** TiTiler stack in `config/`, STAC catalog contract, QGIS read-side plugin (`qgis-plugin/tasco_timeseries_viewer/`)

---

## 1. Premise

The custom pipeline duplicates what `opengeos/qgis-nasa-earthdata-plugin` already ships:

| Custom pipeline file | NASA plugin equivalent |
|---|---|
| `acquire.py` (CMR search + download) | `SearchEarthdataAlgorithm` + `DownloadGranulesAlgorithm` (`processing/algorithms.py`) |
| `process.py` (RGB composite, COG write) | `CreateRgbCogLayerAlgorithm` + `granule_links` / `cog_links_from_links` (`core/workflows.py`) |
| `upload.py` `build_catalog()` | `granules_to_stac_item_collection` + `write_results_stac` (`core/workflows.py`) |

What the NASA plugin does **not** do:
- Push COG bytes to a remote bucket (R2 / S3).
- Merge into a server-side STAC catalog at a stable URL.
- Reproject to EPSG:3857 / clip to AOI for tile-server consumption (TiTiler can do this on-demand, so this is optional).

So the work shrinks to: **one Processing algorithm + one workflows helper + one settings panel**, packaged as a fork of the NASA plugin under `qgis-plugin/tasco_nasa_earthdata/` in this repo.

The custom `tasco_timeseries_viewer` plugin stays as-is for the read side (date browser).

---

## 2. Scope of v1

**In:**
- Take a granules JSON already produced by the NASA plugin's download/search step.
- Build a per-month RGB COG (B04/B03/B02), Fmask-cloud-masked, in EPSG:3857.
- `PUT` each COG to `s3://<bucket>/<source>/<YYYY-MM>/composite.tif`.
- Pull the existing `stac/catalog.json` from the bucket, merge new entries, `PUT` it back.
- Run from QGIS Processing toolbox **and** from a one-click button on the NASA plugin's dock.

**Out (v1 explicitly defers):**
- Multi-tile mosaicking across UTM zones — assume one HLS tile per AOI.
- Concurrent-writer safety on `catalog.json` — single-operator MVP, last-write-wins is acceptable.
- Cleanup of superseded COGs — `catalog.json` is append-only; orphan GC is a v2 chore.
- Auth on the read-side STAC URL — bucket is public-read for now (Nginx adds auth on the tile path, not the catalog path; revisit).

---

## 3. Plugin layout (fork target)

```
qgis-plugin/tasco_nasa_earthdata/          ← fork of opengeos/qgis-nasa-earthdata-plugin
├── nasa_earthdata/
│   ├── core/
│   │   └── workflows.py                   ← + publish_cog_to_bucket(), merge_remote_catalog()
│   ├── processing/
│   │   └── algorithms.py                  ← + PublishToTascoTilesAlgorithm
│   └── dialogs/
│       └── tasco_settings_dialog.py       ← NEW: R2 endpoint, keys, bucket, source name
└── metadata.txt                           ← bumped name: "NASA Earthdata (TASCO fork)"
```

Fork rationale over PR-upstream: the bucket-publish step is TASCO-specific (bucket layout, STAC shape). Upstreaming would require generalizing both. Keep the fork minimal and rebase against upstream `main` quarterly.

---

## 4. The new Processing algorithm

`PublishToTascoTilesAlgorithm` in `processing/algorithms.py`, sibling of `ExportStacAlgorithm`.

**Parameters** (using existing `QgsProcessingParameter*` helpers in the file):

| Name | Type | Notes |
|---|---|---|
| `GRANULES_JSON` | File (JSON) | Output of the existing download step. Same contract as `ExportStacAlgorithm`. |
| `AOI` | Extent | Defaults from QSettings (Hanoi bbox). |
| `SOURCE` | String | Defaults `"sentinel2"`. Becomes the bucket key prefix. |
| `BUCKET` | String | From settings. |
| `DRY_RUN` | Boolean | Skip the `PUT`; print the manifest. |

**processAlgorithm flow:**
1. Load granules JSON.
2. Group by `YYYY-MM` via `granule_temporal_range()` (exists in `workflows.py`).
3. For each month, pick the lowest-cloud granule (reuse `RESULT_EXPORT_FIELDS["cloud_cover"]`).
4. Resolve RGB asset URLs via `cog_links_from_links(granule_links(...))` (both exist).
5. Build a clipped, reprojected RGB COG → call into a new `workflows.publish_cog_to_bucket(...)`.
6. After all months processed, call `workflows.merge_remote_catalog(...)` once.
7. Emit a Processing output `PUBLISHED_COUNT` (int) and `CATALOG_URL` (string).

**Reuse, don't reimplement:**
- The COG-build step should call `CreateRgbCogLayerAlgorithm`'s VRT logic (which already does `/vsicurl/` + `gdal.BuildVRT`), then `gdal.Translate` with `COMPRESS=DEFLATE, TILED=YES, COPY_SRC_OVERVIEWS=YES` to produce the final COG. Avoids the `rio-cogeo` dependency that the current `process.py` carries.
- Cloud masking moves from `process.py:apply_cloud_mask` into a small helper in `workflows.py` — keep the Fmask bit-mask (`fmask & 0b1110`) so we don't change behavior.

---

## 5. The new workflows helpers

Two functions added to `nasa_earthdata/core/workflows.py`, mirroring the file's existing style (module-level functions, JSON-in/JSON-out, no QGIS imports).

```python
def publish_cog_to_bucket(local_cog: Path, *, bucket: str, key: str,
                         s3_client) -> dict:
    """Upload a COG and return {key, etag, size_bytes, content_type}.
    Caller supplies the boto3 client so credentials/endpoint live in one place."""

def merge_remote_catalog(s3_client, *, bucket: str, catalog_key: str,
                        source: str, new_entries: list[dict]) -> dict:
    """Fetch catalog.json (or seed empty), append new entries under sources[<source>],
    de-dupe by (source, date), write back. Returns the merged catalog dict."""
```

Catalog shape stays exactly as the `tasco_timeseries_viewer` plugin's `_parse_catalog` expects:

```json
{
  "type": "Catalog",
  "id": "tasco-imagery-<bucket>",
  "sources": {
    "sentinel2": [
      {"date": "2025-03", "href": "<tile-url-template>", "cog_key": "sentinel2/2025-03/composite.tif"}
    ]
  }
}
```

This is the contract called out in `CLAUDE.md` — both producer and consumer change together when it does.

---

## 6. Credentials (v1)

v1 reads credentials and bucket config from environment variables — same set `upload.py` already uses, so an operator can run the algorithm without any new setup:

| Env var | Example |
|---|---|
| `R2_ENDPOINT` | `https://<acct>.r2.cloudflarestorage.com` |
| `R2_ACCESS_KEY` | — |
| `R2_SECRET_KEY` | — |
| `TASCO_BUCKET` | `tasco-imagery-hanoi` |
| `TASCO_SERVER_URL` | `https://tiles.tasco-internal.vn` |

The boto3 client is built once per algorithm run from these env vars. Missing required ones → `QgsProcessingException` naming the missing variable.

**Do not** put credentials in `metadata.txt`, repo files, or QSettings. For v1 they live only in the operator's shell environment.

## 6.5 v2 polish (deferred — only build when v1 friction justifies it)

The following are intentionally deferred out of v1. None are required for a single-operator MVP; they only earn their cost once a second operator joins or env-var management becomes a daily annoyance.

- **`TascoSettingsDialog`** — QSettings-backed UI panel for endpoint/bucket/server URL, with the secret key stored via `QgsAuthManager` (not plain QSettings).
- **Dock button** in the existing NASA plugin dock: **"Publish to TASCO Tiles…"** that (a) validates the current result set has downloaded granules, (b) opens a confirm dialog showing months / bucket / public URL / dry-run toggle, (c) calls `processing.run("nasa_earthdata:publish_to_tasco_tiles", {...})`. Thin wrapper over the algorithm; no new state.
- **`QgsAuthManager`** integration — needed only after the settings dialog exists, since v1 doesn't store secrets anywhere persistent.

## 7. v1 invocation

No new UI. The operator runs the algorithm from the QGIS Processing toolbox (`NASA Earthdata → Publish to TASCO Tiles`) or from the Python console via `processing.run("nasa_earthdata:publish_to_tasco_tiles", {...})`. Cancellation, log, and history come for free from QGIS Processing.

---

## 8. End-to-end operator flow

```
[NASA plugin dock]
  Search HLS over Hanoi AOI, Jan–Jun 2025, cloud <20%   → results list
  Select all, "Download"                                 → granules JSON + GeoTIFFs on disk

[QGIS Processing toolbox] (v1)
  NASA Earthdata → Publish to TASCO Tiles
    GRANULES_JSON: <path from download step>
    AOI:           105.75,20.95,105.90,21.10
    SOURCE:        sentinel2
                                                            ↓
  Processing log: "6 months published, catalog updated"
                                                            ↓
[tasco_timeseries_viewer]
  Connect → catalog reload → 6 new dates appear in slider
```

(v2 collapses the Processing-toolbox step into a single "Publish to TASCO Tiles…" button in the NASA plugin dock — see §6.5.)

The custom `acquire.py`/`process.py`/`upload.py` scripts become reference implementations only and can be deleted in v2 once the plugin path is proven.

---

## 9. What changes elsewhere in this repo

- `README.md` quick-start §2 ("Run the acquisition pipeline") is replaced by "Install the TASCO NASA Earthdata fork plugin, configure credentials, click Publish."
- `pipeline/` is kept for one release as a fallback / batch path (e.g., running on a server without QGIS) but deprecated in the README.
- `qgis-plugin/tasco_timeseries_viewer/` is unchanged.
- `config/` stack is unchanged — the contract on the bucket is identical.
- `CLAUDE.md` "Pipeline flow" section needs a note pointing at this doc as the primary path.

---

## 10. Open questions

1. **Reprojection to 3857 — keep or drop?** TiTiler can reproject on-the-fly from the source CRS. Dropping the reprojection step makes the COG ~1.4× smaller and eliminates a resample. Worth A/B testing on a Hanoi tile before committing.
2. **Per-granule vs monthly composite.** v1 picks least-cloudy granule per month (matches existing behavior). A `median` aggregate over all in-month granules gives cleaner output but doubles processing time. Defer.
3. **PR upstream?** A generic "Publish to S3-compatible bucket" algorithm — bucket layout and STAC shape as parameters — could be upstreamed. Worth doing after the fork stabilizes (target: month 3).
4. **GeoAgent integration.** Once the algorithm is registered, expose it as a Strands tool so the OpenGeoAgent chat can drive the publish step from a prompt like "publish March 2025 over Hanoi". Trivial follow-up, listed for visibility.
5. **Fork vs companion plugin.** §3 picks a fork. Alternative: ship a small **companion plugin** (`tasco_tiles_publisher`) that `import`s from the installed `nasa_earthdata` package and registers its own Processing algorithm + provider. Tradeoff: companion plugin has a smaller touch surface and zero rebase load against upstream, but couples to upstream's public Python API (which is not officially stable — `core/workflows.py` could rename helpers). Fork has higher maintenance (quarterly rebase) but is insulated from upstream churn. Decide before week 1 — companion is reversible to a fork later; the reverse costs more.

---

## 11. Estimated effort

**v1 (ships the publish flow):**

| Task | Effort |
|---|---|
| Fork plugin (or scaffold companion — see Open Q #5), rename, get it loading in QGIS | 0.5 day |
| `publish_cog_to_bucket` + `merge_remote_catalog` + unit tests on a local MinIO | 1 day |
| `PublishToTascoTilesAlgorithm` (env-var credentials) + reuse of existing VRT/COG code | 0.5 day |
| End-to-end test against staging R2 bucket + viewer | 0.5 day |
| Docs / README rewrite | 0.5 day |
| **v1 total** | **~3 days** |

**v2 (ergonomic polish, deferred — see §6.5):**

| Task | Effort |
|---|---|
| Settings dialog + `QgsAuthManager` integration | 0.5 day |
| Dock button + confirm dialog | 0.5 day |
| **v2 add-on** | **~1 day** |

Compare to the rough cost of maintaining the parallel custom pipeline indefinitely (auth handling, retry logic, manifest schema drift): even v1 alone pays back inside one release. v2 is built only if v1 friction in real use justifies it.

---

## 12. Verification

Each task in §11 ships only when its observable check passes. No "looks good to me."

| Component | Concrete check |
|---|---|
| Fork / companion plugin loads | `metadata.txt` parses; the plugin appears in QGIS Plugin Manager and enables without errors; `nasa_earthdata:publish_to_tasco_tiles` shows in the Processing toolbox. |
| `publish_cog_to_bucket(local, bucket, key, s3)` | Against a local MinIO container: after the call, `aws --endpoint <minio> s3 ls s3://<bucket>/<key>` returns a non-zero size and `ContentType: image/tiff`. Re-running with the same key overwrites without error. |
| `merge_remote_catalog(...)` | Against MinIO with a pre-seeded `catalog.json` containing one entry: after the call, re-fetching `catalog.json` shows the original entry **plus** the new entries under `sources[<source>]`, with no duplicate `(source, date)` tuples. Running twice produces the same catalog (idempotent). |
| `PublishToTascoTilesAlgorithm` | From the QGIS Python console: `processing.run("nasa_earthdata:publish_to_tasco_tiles", {...})` returns a dict with `PUBLISHED_COUNT > 0` and `CATALOG_URL` set. With `DRY_RUN=True` no bytes are written to MinIO. With a missing env var, raises `QgsProcessingException` naming the variable. |
| Cloud masking | A scene with known cloudy pixels: output COG has `nodata = 0` over the masked area; visual inspect in QGIS confirms the mask matches the Fmask bit-1/2/3 footprint. |
| End-to-end against staging R2 | Run the algorithm against the real staging bucket with 2 months of HLS granules. Then open `tasco_timeseries_viewer` in a clean QGIS profile, click **Connect**, confirm: (a) status label turns green (not "demo mode"), (b) the slider exposes exactly the 2 new dates, (c) loading either date displays imagery over Hanoi at z12–z14. |
| README / docs | A reviewer who has never seen this repo follows the updated README quick-start and reaches a working publish + viewer cycle with no out-of-band help. |
