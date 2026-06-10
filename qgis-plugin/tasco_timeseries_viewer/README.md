# TASCO Timeseries Viewer — QGIS Plugin

A QGIS plugin for the TASCO Map Team that connects to the internal timeseries tile server and lets editors browse, load, and compare satellite imagery across dates.

## Installation

1. Copy the `tasco_timeseries_viewer` folder to your QGIS plugins directory:
   - **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`

2. Restart QGIS.

3. Go to **Plugins → Manage and Install Plugins → Installed** and enable **TASCO Timeseries Viewer**.

4. Click the TASCO icon in the toolbar or go to **Plugins → TASCO → TASCO Timeseries Viewer**.

## Configuration

In the dock panel, set the **Server URL** to the internal tile server endpoint (e.g. `https://tiles.tasco-internal.vn`) and click **Connect**.

The plugin fetches the STAC catalog from `{server}/stac/catalog.json` and populates the available imagery sources and dates automatically.

If the server is unavailable, the plugin falls back to **demo mode** with placeholder entries so you can explore the UI.

## Usage

### Loading imagery

1. Select an **Imagery Source** (e.g. `sentinel2`, `planet`).
2. Select a **Date** from the dropdown or drag the slider.
3. Click **Load Selected Date** to add the imagery as an XYZ tile layer.
4. Click **Load Latest** to load the most recent available snapshot.

### Comparing dates

1. Check the **Comparison mode** checkbox.
2. Load two or more dates — they'll stack as separate layers.
3. Use QGIS layer opacity or the **Map Swipe Tool** plugin to compare.

### Removing layers

Click **Remove All Imagery Layers** to clear all TASCO imagery from the project without affecting other layers.

### Navigation

Click **Zoom to Hanoi AOI** to center the map on the Hanoi bounding box (20.95°N–21.10°N, 105.75°E–105.90°E).

## Server API Contract

The plugin expects the tile server to expose:

### STAC Catalog

```
GET {server}/stac/catalog.json
```

Response format (simple custom):

```json
{
  "sources": {
    "sentinel2": [
      {"date": "2024-01", "href": "{server}/sentinel2/2024-01/tiles/{z}/{x}/{y}.png"},
      {"date": "2024-02", "href": "{server}/sentinel2/2024-02/tiles/{z}/{x}/{y}.png"}
    ],
    "planet": [
      {"date": "2024-01", "href": "{server}/planet/2024-01/tiles/{z}/{x}/{y}.png"}
    ]
  }
}
```

Or standard STAC Catalog → Collection → Item hierarchy (the plugin traverses both).

### Tile Endpoint

```
GET {server}/{source}/{date}/tiles/{z}/{x}/{y}.png
```

Returns a 256×256 PNG tile in Web Mercator (EPSG:3857).

## Development

Requires QGIS 3.22+ with PyQGIS. No external Python dependencies — the plugin uses only the Python standard library and PyQGIS/Qt.

To develop locally, symlink the plugin directory into your QGIS plugins folder and use the **Plugin Reloader** plugin to reload after changes.

## Roadmap

- [ ] Support for TMS endpoint in JOSM (export layer URL to clipboard)
- [ ] Integrated swipe comparison without external plugin
- [ ] Layer transparency slider in the panel
- [ ] Thumbnail previews for each date
- [ ] Cloud cover percentage display from STAC metadata
- [ ] Export current view as georeferenced image
