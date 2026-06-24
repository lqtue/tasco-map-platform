# Enterprise Architecture — TASCO Mobility Platform

> **Cập nhật:** 2026-06-18 · **Nguồn:** [okr-ea-2026.06.pdf](./okr-ea-2026.06.pdf) (bản chính thức "VTII MOBILITY — OKR & EA", phần *Kiến trúc hệ thống ứng dụng*) · North star: [tasco-mobility-platform.md](./tasco-mobility-platform.md) · OKR: [okr-2026.06.md](./okr-2026.06.md) · [orchestrator](../README.md)
>
> Bản chép lại trung thực phần EA của tài liệu. Đây là **kiến trúc đích** mà mọi workstream trong repo ladder về — đặc biệt giải nghĩa **"Editor Spatial DB Server" = Temporal Spatial DB** (xem [O3KR2](./okr-2026.06.md)). Stack mặc định: **open-source, clone Yandex/Google/Amap** nhưng tự chủ.

Bốn tầng: **Data Sources → Data Foundation → Serving & APIs → Frontend**. OSM là lớp dữ liệu chuẩn; Valhalla đọc OSM trực tiếp (quyết định họp [2026-06-05](../meeting-minutes/2026-06-05-team-sync.md)).

## 1 · Data Sources Layer (tầng dữ liệu đầu vào)

| # | Nguồn | Vai trò | Stack |
|---|-------|---------|-------|
| 1 | **OSM** (cộng đồng) | Khung xương hình học tuyến đường (geometry & topology); ngõ/ngách/hẻm bản địa | Osmium, Osmosis (`.pbf`) |
| 2 | **Overture Maps** (Meta/MS/AWS/TomTom) | Buildings 3D, address, Places/POI xác thực — bù đứt gãy hình học OSM | DuckDB (SQL trực tiếp trên `.parquet` OMF) |
| 3 | **Viễn thám đa phổ** (Maxar/Planet, quét ~1 tuần/lần, private server) | Vector (U-Net++ phân đoạn mặt đường/bê tông/sông) + Raster (RGB → XYZ tiles); bù vùng OSM out-of-date | GDAL/OGR, PyTorch, SegFormer/Mask2Former/U-Net. *Có thể mua gói bên ngoài (UP42/Skywatch)* |
| 4 | **Ảnh đường phố / MMS** (panoramic + LiDAR) | Trích biển báo, đèn tín hiệu, biển hiệu (Signboard OCR + POI discovery); Street View 360° + Digital Twin | OSM Conflator/RoadMatch, OpenSfM (Lat/Lng tương đối), iD editor fork, YOLO/HRNet/SAM + OCR |
| 5 | **Dữ liệu chính phủ & pháp lý** (Bộ XD, Bộ CA, Sở QHKT, CSGT, đối tác vận tải) | Lớp prior pháp lý theo ngữ cảnh | Tích hợp riêng |
| 6 | **Probe & sensor cộng đồng** (telemetry ẩn danh từ App + xe thông minh) | GPS probes (vị trí/tốc độ → traffic map + ETA), cảm biến quán tính (pitch/barometer → xác định tầng cầu vượt/hầm, sửa GPS drift) | Kafka, Apache Flink, CatBoost (Yandex), Kalman filter |

## 2 · Data Foundation Layer (tầng nền tảng dữ liệu)

- **Raw Data Storage** — vùng đệm (staging) bất biến nhận toàn bộ dữ liệu thô: `.pbf` (OSM), `.parquet` (OMF), GeoTIFF, LiDAR. Stack: **MinIO** (object store) + **Airflow** (điều phối pipeline) + **DuckDB**/GDAL (extract & pre-process — lọc trùng, cắt theo biên VN, đồng bộ schema).
- **Temporal Spatial DB** — *= "Editor Spatial DB Server"*. Nơi lưu dữ liệu đã xử lý phục vụ **biên tập**: cấp dữ liệu cho công cụ editor, **versioning** lịch sử thay đổi từng đối tượng. **PostgreSQL + PostGIS**, tối ưu **write-heavy** + BBOX queries. ← đây là contract giữa pipeline KR2 (Tuệ) và app review/approve KR3 (Quân).
- **Serving Spatial DB** — bản chuẩn hoá, tách độc lập khỏi editor: chỉ phiên bản mới nhất, GIST index, đóng gói Vector Tiles (MVT). **PostgreSQL + PostGIS**, tối ưu **read-heavy** + shared-buffer cache.
- **Place, Address & Metadata** — Address Hierarchy (Tỉnh→Phường→Đường→Số nhà), Temporal POI (toạ độ + định danh + lịch sử), Serving POI (đã dedup/gộp), POI Metadata & Commercial. **PostgreSQL + PostGIS**.
- **Route Graph Data** — đồ thị tuyến đường tĩnh sau conflation, phân mảnh theo tile (Local/Arterial/Highway 3 tầng), con trỏ bộ nhớ trực tiếp (mmap, không SQL). Build: **Valhalla Tile Builder** (C++), **FlatGeobuf / `.pbf`**. Daily/weekly batch từ Serving Spatial DB; zero-downtime swap qua mmap.
- **Real-time Traffic Cache** — cache RAM trạng thái lưu lượng/tốc độ: cặp `Edge_ID : {Speed, Congestion_Factor, Closure_Status}`, **TTL 1–5 phút** (hết hạn → về tốc độ thiết kế). Ingest GPS probes qua Kafka→Flink→upsert. **DragonflyDB** (in-memory đa luồng, thay Redis, độ trễ <1ms cho Valhalla Sif).

## 3 · Serving Layer & APIs

- **Map Tile Service** — đóng gói Serving Spatial DB + POI thành MVT (Mapbox Vector Tiles). **Martin Tile Server (Rust)** (thay Tippecanoe/Mapbox sau khi Mapbox chuyển thương mại) — phục vụ cả vector + raster tile, tương thích MapLibre. Cung cấp basemap tiles, dynamic tiles, style JSON, glyphs, sprites, 3D building tiles, offline map packages.
- **Place Searching** — geocoding + POI search trên **OpenSearch/ElasticSearch**: autocomplete, fuzzy matching + NLP sửa lỗi tiếng Việt, spatial scoring, localization theo cấu trúc hành chính VN. APIs: geocoding (search/autocomplete/reverse), Place/POI (category/nearby/detail/photos/opening-hours/reviews), crowdsourcing (suggest-edit/owner-claim). Stack: OpenSearch + Address Parser (ML) + Spring Cloud Gateway.
- **Routing & Navigation Engine** — stateless, đọc Route Graph Data (mmap) + nạp Real-time Traffic từ DragonflyDB. Đa phương tiện (xe máy/ô tô/xe tải/xe đạp/đi bộ) với costing model riêng. APIs: routing, matrix, optimized-route (TSP), isochrone, map-matching. **Valhalla**: Loki (map-match) / Thor (A* + Contraction Hierarchies) / Sif (costing engine) / Odin (turn-by-turn) + **PrimeServer** (HTTP bất đồng bộ).

## 4 · Frontend Application Layer

**MapLibre GL** (clone MapLibre tuỳ biến — O1KR2, lộ trình 2027): render vector tile WebGL/WebGPU 60fps 2D/3D, dynamic styling, route/traffic visualization, turn-by-turn UI, location smoothing (interpolation khử GPS drift). Cung cấp **Map SDKs** (Web React/Vue + Mobile Flutter/Native) + interactive control APIs. Stack: MapLibre GL JS + MapLibre Native (C++) + MVT spec + **Turf.js** (geospatial client-side).

## Sơ đồ luồng (rút gọn)

```
OSM/Overture/Raster/StreetView/Regulatory/Probe
        │  (Osmium·DuckDB·GDAL·YOLO·Kafka)
        ▼
   Raw Data Storage (MinIO·Airflow·DuckDB)
        ▼
   Temporal Spatial DB  ──► Route Graph Builder ──► Route Graph Data
   (Postgres+PostGIS,         (Valhalla Tile Builder)   (FlatGeobuf/mmap)
    versioned, EDITOR)                                        │
        │                                              Real-time Traffic
        ▼                                              Cache (DragonflyDB)
   Serving Spatial DB ── Place/Address/Metadata               │
        │                      │                              │
        ▼                      ▼                              ▼
   Map Tile Service     Location Search          Routing/Nav/ETA
   (Martin)             (OpenSearch)             (Valhalla)
        └──────────────┬───────────────────────────┘
                       ▼
            Web/App Application (MapLibre, WebGL)
```

## Kiến trúc tham chiếu

Stack trên là bản tự chủ của **3 mô hình tham chiếu** (PDF chép chi tiết từng tầng):

- **Yandex** — Computer Vision (Nirvana ML, HRNet/U-Net++), DataLens ETL, Yandex Query/Tables (Internal Spatial DB versioned), Vector Engine (renderer C++), **ClickHouse** (serving tiles), YDB (POI/metadata NewSQL), Logbroker (message queue), **CatBoost** (ETA), Tile Service HTTP/3+QUIC, MapKit SDK + WebGL. *(Tài liệu tham chiếu UX chính.)*
- **Google Maps** — Cloud Vision AI, Dataflow/Apache Beam, **S2 Geometry** (thay H3), Bigtable (tiles), **Spanner** (POI/address nhất quán toàn cầu), Pub/Sub, TensorFlow (ETA), Memorystore/Redis, Maps Tile/Places/Routing API, Global Edge CDN, Maps SDK + Skia.
- **A-Map (Amap/Alibaba)** — Vision AI (SegFormer/Swin, lane-level + 3D), City Brain IoT, MaxCompute (ODPS petabyte/ngày), Ganos Engine (3D Digital Twin), TableStore/PolarDB, **Blink** (Flink tối ưu), City Brain AI traffic, ApsaraDB Redis, Amap Tile/Search/Routing (lane-level nav), Cloud CDN + Weex SDK.
