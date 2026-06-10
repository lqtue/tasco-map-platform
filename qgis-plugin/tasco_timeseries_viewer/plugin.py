"""
TASCO Timeseries Viewer — QGIS Plugin
Connects to the TASCO internal tile server and lets editors
browse satellite imagery by date, load layers, and compare.
"""

import json
import os
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import (
    QAction, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QSlider, QGroupBox,
    QLineEdit, QMessageBox, QCheckBox, QFrame, QSizePolicy,
    QProgressBar,
)
from qgis.core import (
    QgsRasterLayer, QgsProject, QgsCoordinateReferenceSystem,
    QgsRectangle, Qgis,
)


# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
DEFAULT_SERVER = "https://tiles.tasco-internal.vn"
STAC_CATALOG_PATH = "/stac/catalog.json"
TILE_URL_TEMPLATE = "{server}/{source}/{date}/tiles/{{z}}/{{x}}/{{y}}.png"
SETTINGS_PREFIX = "tasco_timeseries/"


class TascoTimeseriesViewer:
    """Main plugin entry point."""

    def __init__(self, iface):
        self.iface = iface
        self.dock = None
        self.action = None
        self.panel = None
        self.plugin_dir = os.path.dirname(__file__)

    # -- Lifecycle -----------------------------------------------------------

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(icon, "TASCO Timeseries Viewer", self.iface.mainWindow())
        self.action.triggered.connect(self.toggle_panel)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("TASCO", self.action)

    def unload(self):
        self.iface.removePluginMenu("TASCO", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock = None

    # -- Panel ---------------------------------------------------------------

    def toggle_panel(self):
        if self.dock is None:
            self.dock = QDockWidget("TASCO Imagery", self.iface.mainWindow())
            self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
            self.panel = TimeseriesPanel(self.iface)
            self.dock.setWidget(self.panel)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        else:
            self.dock.setVisible(not self.dock.isVisible())


# ---------------------------------------------------------------------------
# Panel widget
# ---------------------------------------------------------------------------

class TimeseriesPanel(QWidget):
    """Dock widget content: server config, source/date selection, layer actions."""

    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.catalog = {}          # source_name -> [{"date": ..., "url": ...}, ...]
        self.loaded_layers = {}    # "source/date" -> layer_id
        self._build_ui()
        self._load_settings()
        self._fetch_catalog()

    # -- UI construction -----------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # --- Server config ---
        grp_server = QGroupBox("Tile Server")
        srv_layout = QVBoxLayout()

        lbl = QLabel("Server URL:")
        self.txt_server = QLineEdit(DEFAULT_SERVER)
        self.txt_server.setPlaceholderText("https://tiles.example.com")
        btn_connect = QPushButton("Connect")
        btn_connect.clicked.connect(self._fetch_catalog)

        srv_layout.addWidget(lbl)
        srv_layout.addWidget(self.txt_server)
        srv_layout.addWidget(btn_connect)
        grp_server.setLayout(srv_layout)
        layout.addWidget(grp_server)

        # --- Status ---
        self.lbl_status = QLabel("Not connected")
        self.lbl_status.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.lbl_status)

        # --- Source selection ---
        grp_source = QGroupBox("Imagery Source")
        src_layout = QVBoxLayout()

        self.cmb_source = QComboBox()
        self.cmb_source.currentIndexChanged.connect(self._on_source_changed)
        src_layout.addWidget(self.cmb_source)

        grp_source.setLayout(src_layout)
        layout.addWidget(grp_source)

        # --- Date selection ---
        grp_date = QGroupBox("Date")
        date_layout = QVBoxLayout()

        self.cmb_date = QComboBox()
        date_layout.addWidget(self.cmb_date)

        # Slider for quick scrubbing
        slider_row = QHBoxLayout()
        self.lbl_slider_start = QLabel("")
        self.sld_date = QSlider(Qt.Horizontal)
        self.sld_date.setMinimum(0)
        self.sld_date.valueChanged.connect(self._on_slider_changed)
        self.lbl_slider_end = QLabel("")
        slider_row.addWidget(self.lbl_slider_start)
        slider_row.addWidget(self.sld_date)
        slider_row.addWidget(self.lbl_slider_end)
        date_layout.addLayout(slider_row)

        grp_date.setLayout(date_layout)
        layout.addWidget(grp_date)

        # --- Actions ---
        grp_actions = QGroupBox("Actions")
        act_layout = QVBoxLayout()

        btn_load = QPushButton("Load Selected Date")
        btn_load.setStyleSheet("font-weight: bold;")
        btn_load.clicked.connect(self._load_layer)
        act_layout.addWidget(btn_load)

        btn_latest = QPushButton("Load Latest")
        btn_latest.clicked.connect(self._load_latest)
        act_layout.addWidget(btn_latest)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        act_layout.addWidget(line)

        # Comparison mode
        self.chk_compare = QCheckBox("Comparison mode")
        self.chk_compare.setToolTip(
            "When enabled, loading a new date keeps the previous layer visible "
            "so you can compare using layer opacity or the map swipe tool."
        )
        act_layout.addWidget(self.chk_compare)

        btn_remove = QPushButton("Remove All Imagery Layers")
        btn_remove.clicked.connect(self._remove_all_layers)
        act_layout.addWidget(btn_remove)

        grp_actions.setLayout(act_layout)
        layout.addWidget(grp_actions)

        # --- Layer info ---
        grp_info = QGroupBox("Loaded Layers")
        info_layout = QVBoxLayout()
        self.lbl_layers = QLabel("None")
        self.lbl_layers.setWordWrap(True)
        info_layout.addWidget(self.lbl_layers)
        grp_info.setLayout(info_layout)
        layout.addWidget(grp_info)

        # Stretch at bottom
        layout.addStretch()

        # --- Zoom to AOI ---
        btn_zoom = QPushButton("Zoom to Hanoi AOI")
        btn_zoom.clicked.connect(self._zoom_to_aoi)
        layout.addWidget(btn_zoom)

        self.setLayout(layout)

    # -- Settings persistence ------------------------------------------------

    def _load_settings(self):
        s = QSettings()
        server = s.value(SETTINGS_PREFIX + "server", DEFAULT_SERVER)
        self.txt_server.setText(server)

    def _save_settings(self):
        s = QSettings()
        s.setValue(SETTINGS_PREFIX + "server", self.txt_server.text().strip())

    # -- STAC catalog --------------------------------------------------------

    def _fetch_catalog(self):
        """Fetch the STAC catalog from the tile server and populate source/date combos."""
        server = self.txt_server.text().strip().rstrip("/")
        self._save_settings()
        url = server + STAC_CATALOG_PATH

        self.lbl_status.setText("Connecting...")
        self.lbl_status.setStyleSheet("color: #888; font-style: italic;")

        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except (URLError, json.JSONDecodeError, Exception) as e:
            self.lbl_status.setText(f"Connection failed: {e}")
            self.lbl_status.setStyleSheet("color: red; font-style: italic;")

            # Fall back to offline/demo mode with mock catalog
            self._load_demo_catalog(server)
            return

        self._parse_catalog(data, server)

    def _load_demo_catalog(self, server):
        """Load a demo catalog so the plugin is functional before the server is live."""
        self.catalog = {
            "sentinel2": [],
            "planet": [],
        }
        # Generate demo Sentinel-2 monthly entries for 2023-01 through 2025-05
        for year in range(2023, 2026):
            end_month = 5 if year == 2025 else 12
            for month in range(1, end_month + 1):
                date_str = f"{year}-{month:02d}"
                tile_url = f"{server}/sentinel2/{date_str}/tiles/{{z}}/{{x}}/{{y}}.png"
                self.catalog["sentinel2"].append({
                    "date": date_str,
                    "url": tile_url,
                    "label": f"Sentinel-2  {date_str}",
                })

        self.lbl_status.setText("Demo mode (server not available)")
        self.lbl_status.setStyleSheet("color: #b58900; font-style: italic;")
        self._populate_sources()

    def _parse_catalog(self, data, server):
        """Parse a STAC catalog JSON into the internal catalog dict."""
        self.catalog = {}

        # Expect either a STAC Catalog with child links to Collections,
        # or a flat structure with items grouped by source.
        # Support a simple custom format:
        # { "sources": { "sentinel2": [ {"date": "2024-01", "href": "..."} ] } }
        if "sources" in data:
            for source_name, items in data["sources"].items():
                entries = []
                for item in sorted(items, key=lambda x: x.get("date", "")):
                    date_str = item.get("date", item.get("datetime", ""))[:7]
                    href = item.get("href", item.get("url", ""))
                    if not href:
                        href = f"{server}/{source_name}/{date_str}/tiles/{{z}}/{{x}}/{{y}}.png"
                    entries.append({
                        "date": date_str,
                        "url": href,
                        "label": f"{source_name}  {date_str}",
                    })
                self.catalog[source_name] = entries
        else:
            # Try standard STAC catalog → collections → items
            self._parse_stac_standard(data, server)

        self.lbl_status.setText(f"Connected — {sum(len(v) for v in self.catalog.values())} snapshots")
        self.lbl_status.setStyleSheet("color: green; font-style: italic;")
        self._populate_sources()

    def _parse_stac_standard(self, data, server):
        """Parse a standard STAC Catalog with links to collections."""
        links = data.get("links", [])
        child_links = [l for l in links if l.get("rel") == "child"]

        for link in child_links:
            collection_name = link.get("title", link.get("href", "").split("/")[-1])
            try:
                req = Request(link["href"], headers={"Accept": "application/json"})
                with urlopen(req, timeout=10) as resp:
                    coll = json.loads(resp.read().decode())
            except Exception:
                continue

            entries = []
            item_links = [l for l in coll.get("links", []) if l.get("rel") == "item"]
            for il in sorted(item_links, key=lambda x: x.get("datetime", x.get("href", ""))):
                try:
                    req2 = Request(il["href"], headers={"Accept": "application/json"})
                    with urlopen(req2, timeout=10) as resp2:
                        item = json.loads(resp2.read().decode())
                except Exception:
                    continue

                dt = item.get("properties", {}).get("datetime", "")[:7]
                assets = item.get("assets", {})
                visual = assets.get("visual", assets.get("rendered", {}))
                href = visual.get("href", "")
                if not href:
                    href = f"{server}/{collection_name}/{dt}/tiles/{{z}}/{{x}}/{{y}}.png"

                entries.append({
                    "date": dt,
                    "url": href,
                    "label": f"{collection_name}  {dt}",
                })

            if entries:
                self.catalog[collection_name] = entries

    # -- UI population -------------------------------------------------------

    def _populate_sources(self):
        self.cmb_source.blockSignals(True)
        self.cmb_source.clear()
        for source_name in sorted(self.catalog.keys()):
            count = len(self.catalog[source_name])
            self.cmb_source.addItem(f"{source_name} ({count} dates)", source_name)
        self.cmb_source.blockSignals(False)
        self._on_source_changed()

    def _on_source_changed(self):
        source = self.cmb_source.currentData()
        if not source or source not in self.catalog:
            return

        entries = self.catalog[source]
        self.cmb_date.blockSignals(True)
        self.cmb_date.clear()
        for entry in entries:
            self.cmb_date.addItem(entry["date"], entry)
        self.cmb_date.blockSignals(False)

        # Update slider
        if entries:
            self.sld_date.setMaximum(len(entries) - 1)
            self.sld_date.setValue(len(entries) - 1)  # default to latest
            self.lbl_slider_start.setText(entries[0]["date"])
            self.lbl_slider_end.setText(entries[-1]["date"])
            self.cmb_date.setCurrentIndex(len(entries) - 1)

    def _on_slider_changed(self, value):
        if value < self.cmb_date.count():
            self.cmb_date.setCurrentIndex(value)

    # -- Layer management ----------------------------------------------------

    def _load_layer(self):
        """Add the selected date as an XYZ tile layer."""
        entry = self.cmb_date.currentData()
        if not entry:
            return

        source = self.cmb_source.currentData()
        layer_key = f"{source}/{entry['date']}"

        # Check if already loaded
        if layer_key in self.loaded_layers:
            layer = QgsProject.instance().mapLayer(self.loaded_layers[layer_key])
            if layer:
                self.iface.setActiveLayer(layer)
                self.iface.messageBar().pushMessage(
                    "TASCO", f"Layer already loaded: {layer_key}", level=Qgis.Info, duration=3
                )
                return

        # Remove previous imagery layers if not in comparison mode
        if not self.chk_compare.isChecked():
            self._remove_all_layers()

        # Build XYZ URL — QGIS expects {x}, {y}, {z} in the URL
        tile_url = entry["url"]
        # Ensure QGIS-style placeholders
        tile_url = tile_url.replace("{x}", "{x}").replace("{y}", "{y}").replace("{z}", "{z}")

        # Create XYZ raster layer
        uri = f"type=xyz&url={tile_url}&zmin=5&zmax=18"
        layer_name = f"TASCO {source} {entry['date']}"
        layer = QgsRasterLayer(uri, layer_name, "wms")

        if not layer.isValid():
            self.iface.messageBar().pushMessage(
                "TASCO", f"Failed to load layer: {tile_url}", level=Qgis.Warning, duration=5
            )
            return

        QgsProject.instance().addMapLayer(layer)
        self.loaded_layers[layer_key] = layer.id()
        self._update_layer_info()

        self.iface.messageBar().pushMessage(
            "TASCO", f"Loaded: {layer_name}", level=Qgis.Success, duration=3
        )

    def _load_latest(self):
        """Load the most recent date for the current source."""
        if self.cmb_date.count() > 0:
            self.cmb_date.setCurrentIndex(self.cmb_date.count() - 1)
            self.sld_date.setValue(self.cmb_date.count() - 1)
            self._load_layer()

    def _remove_all_layers(self):
        """Remove all TASCO imagery layers from the project."""
        project = QgsProject.instance()
        for key, layer_id in list(self.loaded_layers.items()):
            layer = project.mapLayer(layer_id)
            if layer:
                project.removeMapLayer(layer_id)
        self.loaded_layers.clear()
        self._update_layer_info()

    def _update_layer_info(self):
        """Update the loaded layers display."""
        if not self.loaded_layers:
            self.lbl_layers.setText("None")
        else:
            lines = sorted(self.loaded_layers.keys())
            self.lbl_layers.setText("\n".join(lines))

    # -- Navigation ----------------------------------------------------------

    def _zoom_to_aoi(self):
        """Zoom the map canvas to the Hanoi AOI."""
        # Hanoi urban core bounding box in EPSG:4326
        # 20.95°N – 21.10°N, 105.75°E – 105.90°E
        canvas = self.iface.mapCanvas()
        crs_4326 = QgsCoordinateReferenceSystem("EPSG:4326")

        from qgis.core import QgsCoordinateTransform
        transform = QgsCoordinateTransform(
            crs_4326,
            canvas.mapSettings().destinationCrs(),
            QgsProject.instance(),
        )

        extent = QgsRectangle(105.75, 20.95, 105.90, 21.10)
        transformed = transform.transformBoundingBox(extent)
        canvas.setExtent(transformed)
        canvas.refresh()
