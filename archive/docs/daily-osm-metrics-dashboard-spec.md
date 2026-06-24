# Daily OSM Metrics Dashboard — Design Report

**Tác giả:** Tuệ (Geospatial Data Analyst)  
**Ngày:** 2026-06-18 (cập nhật: audit scite 2026-06-18)  
**Đối chiếu:** [OKR 2026.06](./vision/okr-2026.06.md) · [STATUS_REPORT_2026-06-18](./STATUS_REPORT_2026-06-18.md) · [orchestrator](./README.md)

---

## 1. Bối cảnh và động lực

Mục tiêu vận hành O3 đặt ra yêu cầu biên tập và đo lường chất lượng dữ liệu OSM theo ngày — tốc độ, biển báo, tên đường, địa giới — trên toàn quốc lộ/cao tốc. Hiện tại, team chỉ có snapshot tĩnh (chạy tay khi cần) và không có cách theo dõi tốc độ cải thiện hoặc phát hiện regression sau khi dữ liệu được upload lên OSM.

Yêu cầu từ Tuệ: **"xây dựng dashboard y chang và detail hơn Grab, hằng ngày pull pbf về load lên"** — tham chiếu Telenav OSM Metrics Dashboard (SOTM 2018, youtu.be/FDEIcMyV0mM) và Mapbox nav metrics (youtu.be/vpw4Lu5y2DA).

> **Lưu ý khoa học quan trọng:** Barrington-Leigh & Millard-Ball (2017) ước tính OSM đạt ~83% **feature completeness** (tuyến đường có tồn tại) toàn cầu. Tuy nhiên đây là tiêu chí khác với **attribute completeness** (tag tồn tại và đúng). VN 87% thiếu `maxspeed` là vấn đề attribute completeness trên nền feature completeness đã ổn — cần phân biệt khi trình bày với lãnh đạo.

Dashboard này phục vụ hai nhóm người dùng:
- **Team MapOps (Duy, Việt, Phương)** — biết hôm nay nên tập trung vào đoạn đường nào
- **Anh Phụng / ban lãnh đạo** — thấy được tốc độ cải thiện dữ liệu theo thời gian (OKR progress)

> **Phạm vi đã mở rộng:** report bắt đầu là spec dashboard metrics, nay bao trùm **kiến trúc hệ MapOps** — hub editor (§5.4), tầng dữ liệu & đồng bộ OSM (§5.5), pipeline biển báo (§5.6), và mô hình Human-in-the-Loop (§11). Dashboard metrics là *một* mặt của hệ này.

---

## 2. Tham chiếu ngành

### 2.1 Telenav OSM Metrics Dashboard (SOTM 2018)

Telenav (nay thuộc Grab) xây dựng pipeline hằng ngày pull PBF Geofabrik → tính coverage cho các thuộc tính điều hướng quan trọng: **tốc độ giới hạn, oneway, turn restriction, tên đường, số làn, barrier**. Dashboard hiển thị:

- **Tỷ lệ coverage theo highway class** (motorway → tertiary) × từng thuộc tính
- **Xu hướng theo ngày/tuần** — đường cong cải thiện
- **Phát hiện thay đổi (delta)** — km được thêm/mất kể từ hôm qua
- **Drill-down địa lý** — quốc gia → bang/tỉnh → thành phố

Toolchain đã biết: osmosis/osmconvert/osmfilter + PostgreSQL/PostGIS + Python. Tần suất: daily (Geofabrik cập nhật daily diff).

### 2.2 Grab Map Quality (SE Asia context)

Grab theo dõi mạng lưới đường VN/ID/PH/TH/SG/MY ở độ phân giải province. Ngoài maxspeed/name, họ track **turn restriction completeness** và **address coverage** (house number + street name). Điểm khác biệt: Grab có một lớp **ground-truth từ GPS tài xế** để validate xem turn restriction có thực sự đúng không.

TASCO hiện chưa có GPS fleet → lớp validation này là tương lai (Mapillary public GPS là nguồn thay thế gần nhất, đang dùng trong `traffic/maxspeed/`).

### 2.3 Khoảng cách hiện tại của repo

| Năng lực | Trạng thái |
|---|---|
| Coverage calculation | ✅ Đầy đủ (`maxspeed/name/morphology/route_coverage.py`) |
| Per-province breakdown | ✅ Tên đường (`province_name_coverage.py`); ❌ maxspeed per province |
| Per-road (quốc lộ) | ✅ `route_coverage.py` (km, maxspeed%, connectivity) |
| Time-series / daily trend | ❌ Không có — chỉ snapshot |
| Delta detection | ❌ Không có |
| Signs / signals count | ⚠️ Parquet có, chưa tích hợp dashboard |
| Daily automation (cron) | ❌ Không có |
| Unified view | ⚠️ Metrics phân tán (`app_maxspeed.py`, `dashboards/app.py`); **lane visualizer = hub được chọn** (§5.4), không phải mảnh cần gộp bỏ |

### 2.4 Cơ sở khoa học — nền tảng từ nghiên cứu đã kiểm chứng

Các thiết kế metric và pipeline trong báo cáo này có chỗ dựa trong nghiên cứu peer-reviewed về chất lượng dữ liệu OSM (được xác minh qua scite, 2026-06-18).

#### 2.4.1 Khung đánh giá chất lượng OSM (Barron et al., 2013)

Barron, Neis & Zipf (2013) đề xuất framework intrinsic gồm hơn 25 chỉ số chia thành 6 nhóm, trong đó nhóm **"routing and navigation"** gồm: completeness của mạng đường, attribute accuracy của đường (tên, số làn, hướng một chiều), và roads without a name or route number. Framework này không cần dataset tham chiếu — đánh giá hoàn toàn từ lịch sử dữ liệu OSM. Đây là khung được dẫn chiếu nhiều nhất trong lĩnh vực (384 bài trích dẫn). Dashboard này thực hiện đúng một phần nhóm "routing and navigation" cho VN.

#### 2.4.2 Phân biệt feature completeness và attribute completeness

Barrington-Leigh & Millard-Ball (2017) ước tính OSM đạt ~83% về **feature completeness** (tuyến đường có tồn tại hay không) ở cấp toàn cầu. Tuy nhiên, Keller et al. (2020) nhận xét rõ: *"completeness varies significantly between the different countries worldwide, both in terms of the feature completeness and the **attribute** completeness"*. Việt Nam với 87% quốc lộ thiếu `maxspeed` là trường hợp điển hình: đường tồn tại trong OSM nhưng thiếu thuộc tính điều hướng — khoảng trống này chính là mục tiêu của O3KR1.

Gatea & Al-Bakri (2023) đo lường OSM tại Iraq cho thấy: dù completeness hình học rất cao (>98%), tỷ lệ tên đường (name tag) trên đường không phải trục chính vẫn rất thấp — tương tự tình trạng VN ở lớp `secondary`/`tertiary`.

#### 2.4.3 `maxspeed` và `name` là thuộc tính navigation thiết yếu

Almendros-Jiménez & Becerra-Terón (2018) định nghĩa completeness cho navigation OSM gồm: *"the occurrence of name, direction flows (oneway) and maximum speed (maxspeed) of highways... are essential for a precise navigational information."* Vierø et al. (2024) phân tích tag completeness trên mạng đường Đan Mạch và xác nhận `maxspeed` có mức độ biến thiên từ 0–100% theo không gian địa lý — nghĩa là thiếu maxspeed không phải lỗi ngẫu nhiên mà có tương quan địa lý, có thể ưu tiên theo tỉnh.

#### 2.4.4 Connectivity là chiều chất lượng độc lập

Zhang, Mao & Han (2024) lập luận: *"Connectivity is an important attribute in road network topology, but there is no index to evaluate this attribute in the quality evaluation of road network data"* và đề xuất **relative connectivity** như một chỉ số chất lượng chuyên biệt. Điều này trực tiếp ủng hộ thành phần `connectivity` (số connected components) trong completeness score của dashboard: một quốc lộ bị đứt đoạn (components > 1) không chỉ thiếu tag mà còn sai về topology.

#### 2.4.5 Weighted composite index là phương pháp hợp lệ

El Rashidy & Grant-Muller (2019) xây dựng **composite resilience index** cho mạng đường giao thông bằng cách kết hợp có trọng số các chỉ số (redundancy, vulnerability, mobility), và kiểm tra cả equal weighting lẫn PCA weighting. Kết quả cho thấy composite index phản ánh tốt hơn hiện trạng mạng đường so với từng chỉ số đơn lẻ. Completeness score của dashboard (`w1*maxspeed% + w2*name% + w3*connectivity`) là ứng dụng cùng nguyên lý với trọng số điều chỉnh qua slider.

#### 2.4.6 Theo dõi time-series / delta là phương pháp đã được thiết lập

Bres, Peralta & Le-Guilcher (2023) phân tích sự tiến hóa của mạng đường OSM theo thời gian qua nhiều snapshot, ghi nhận các vùng có tần suất thay đổi khác nhau theo mật độ dân số. Nasiri et al. (2018) sử dụng lịch sử đóng góp OSM như một công cụ đánh giá chất lượng — dữ liệu lịch sử là nguồn thông tin chất lượng nội tại (intrinsic). Cả hai xác nhận rằng kiến trúc `history/YYYY-MM-DD.json` + delta detection là phương pháp khoa học, không chỉ là dashboard cosmetics.

---

## 3. Alignment với OKR 2026.06

| OKR item | Metric cần đo | Nguồn dữ liệu | Tần suất |
|---|---|---|---|
| O3KR1.1 — giới hạn tốc độ | `maxspeed` coverage % × highway class + per quốc lộ | `maxspeed_coverage.py`, `route_coverage.py` | Daily |
| O3KR1.1 — đèn tín hiệu | Số nút `highway=traffic_signals` trên quốc lộ/cao tốc | baseline PBF | Daily |
| O3KR1.1 — biển cấm (6 loại) | Count per sign type từ Mapillary + OSM `restriction=*` | `mapillary_signs.py` + OSM | Daily |
| O3KR1.2 — tên đường | `name` coverage % × highway class + per province | `name_coverage.py`, `province_name_coverage.py` | Daily |
| O3KR1.2 — địa giới | Admin ward count, merger coverage | `admin-poi/geocode/` | Weekly (stable) |
| O3KR2.1 — OSM → Editor DB | Số way đã ingest vs tổng way | Editor DB (khi có) | Daily |
| O3KR3.3 — per-route checker | Per-route completeness score (maxspeed + name + lanes) | `route_coverage.py` | Daily |

**Lưu ý scope:** O3KR1.1 bao gồm tín hiệu đèn và 6 loại biển cấm — nhưng hiện chưa có script tính coverage OSM cho các tag này. Dashboard spec phải dự phòng slot cho các metric này dù script chưa tồn tại.

---

## 4. Thiết kế metric

### 4.1 Taxonomy đầy đủ

```
VN-wide
  ├── Mạng đường (tertiary+)
  │     ├── maxspeed_coverage_%        [per class: motorway/trunk/primary/secondary/tertiary]
  │     ├── name_coverage_%            [per class]
  │     ├── lanes_coverage_%           [per class]
  │     ├── oneway_km                  [per class]
  │     └── signal_node_count          [total + per class adjacency]
  ├── Theo tỉnh/thành (34 tỉnh)
  │     ├── maxspeed_coverage_%
  │     └── name_coverage_%
  ├── Theo quốc lộ / cao tốc (route relations)
  │     ├── ref, centerline_km, member_km
  │     ├── maxspeed_%
  │     ├── connectivity (component count)
  │     └── completeness_score (tổng hợp)
  └── Biển báo (Mapillary)
        ├── speed_sign_count
        ├── residential_sign_count     [khi có]
        └── no_overtaking_sign_count   [khi có]
```

### 4.2 Completeness score (per quốc lộ)

Điểm tổng hợp để xếp hạng ưu tiên cho MapOps:

```
score = w1 * maxspeed_% + w2 * name_% + w3 * (1 if components==1 else 0)
```

Trọng số mặc định: `w1=0.6, w2=0.3, w3=0.1` (maxspeed là ưu tiên theo scope pivot 06-15). Các trọng số là slider trong dashboard — không hard-code.

**Nền tảng khoa học:** Phương pháp composite index có trọng số được El Rashidy & Grant-Muller (2019) kiểm chứng cho mạng đường giao thông; Almendros-Jiménez & Becerra-Terón (2018) xác nhận `maxspeed` và `name` là hai thuộc tính navigation thiết yếu; thành phần `connectivity` được Zhang et al. (2024) đề xuất như một chiều chất lượng topology độc lập (xem §2.4).

### 4.3 Delta (change detection)

Mỗi lần chạy daily so sánh với run hôm qua:

```
delta_maxspeed_km  = today.maxspeed_km  - yesterday.maxspeed_km
delta_maxspeed_%   = today.maxspeed_%   - yesterday.maxspeed_%
```

Delta âm (dữ liệu bị mất) cần được highlight đỏ — có thể là vandalism hoặc revert.

---

## 5. Kiến trúc pipeline

### 5.1 Luồng dữ liệu

```
[Cron 02:00 hằng ngày]
        │
        ▼
run.sh  ─── wget Geofabrik VN PBF (nếu newer) ──► vietnam-latest.osm.pbf
        │
        ├── osmium tags-filter → vn-major.osm.pbf (tertiary+)
        │
        ├── osmium export -f geojsonseq
        │         │
        │         ├──► maxspeed_coverage.py       → maxspeed_coverage_result.json
        │         ├──► name_coverage.py           → name_coverage_result.json
        │         ├──► morphology_coverage.py     → morphology_coverage_result.json
        │         └──► province_name_coverage.py  → province_name_result.json
        │
        ├── route_coverage.py (PBF trực tiếp)    → route_coverage_result.json
        │
        ├── [NEW] province_maxspeed_coverage.py  → province_maxspeed_result.json
        │
        └── [NEW] history_append.sh              → history/YYYY-MM-DD.json
                                                    (snapshot ngày + delta vs hôm qua)
```

### 5.2 Schema `history/YYYY-MM-DD.json`

```json
{
  "date": "2026-06-18",
  "vn_wide": {
    "maxspeed_km": 17258.3,
    "maxspeed_pct": 12.9,
    "name_km": 89423.1,
    "name_pct": 66.8,
    "total_km": 133771.0
  },
  "delta": {
    "maxspeed_km": +12.4,
    "maxspeed_pct": +0.009
  },
  "by_class": { ... },
  "by_province": { ... },
  "by_route": { ... }
}
```

File history là append-only. Dashboard đọc toàn bộ `history/*.json` để vẽ trend chart.

### 5.3 Cron entry (đề xuất)

```bash
# /etc/cron.d/tasco-osm-metrics  (hoặc launchd plist trên Mac)
0 2 * * * cd /path/to/tasco-map-platform && bash traffic/maxspeed/baseline/run.sh \
  && python3 traffic/maxspeed/baseline/history_append.py
```

### 5.4 Kiến trúc hệ thống tổng thể — một hub, nhiều tầng

Dashboard metrics không đứng một mình; nó là **một mặt** của hệ MapOps. Mô hình phân tầng:

```
NGUỒN
  PBF Geofabrik VN hằng ngày ──► run.sh + script coverage ──► metrics + worklist xếp hạng
                                                                  │
                                                                  ▼
HUB  ── Lane visualizer (buồng lái MapOps) ─────────────────────────────────────
  • Dashboard:  completeness score, worklist, tiến độ per-road
  • Sửa phi-hình-học:  maxspeed / name / biển trên way sẵn có  ← thắng nhanh nhất
  • Tầng bằng chứng, thay-thế-được (swappable):
       - Street-view:  Mapillary nay ──► SV server riêng sau
       - Vệ tinh:      tầng XYZ tile sau  ◄── chính là legacy TiTiler/R2 server
  └─ deeplink ra ngoài cho việc cần hình học ─┐
                                              ▼
SỬA HÌNH HỌC (không dựng lại)
  JOSM / RapiD / iD  — vẽ lại way, split, đường mới

PIPELINE SAU (việc ML/hình học thực sự)
  Biển Mapillary ──► dedup + tam giác đạc vị trí biển ──►
       snap vào đoạn đường + hướng ──► suy maxspeed theo đoạn (xem §5.6)
```

**Vì sao phi-hình-học trước:** gap 87% là **attribute completeness** (tag thiếu trên đường *đã tồn tại*), không phải feature completeness (§2.4.2). Gắn `maxspeed=80` vào way sẵn có là một edit thuộc tính, không vẽ gì — task lợi suất cao nhất, kỹ năng thấp nhất, hợp với crowd trả-theo-km. Hình học (conflict cao) ủy thác cho JOSM/iD vốn tự kiểm version với OSM.

**Điểm hợp nhất đáng ghi:** "sat img qua XYZ tile sau" = đúng thứ stack **`legacy/`** (TiTiler + R2 + Nginx) tạo ra. Map của lane visualizer là Leaflet → thêm 1 dòng `L.tileLayer(url)`. `scripts/josm-imagery.xml` đã cấp cùng tile đó cho JOSM. Vậy việc legacy không chết — nó là tầng bằng chứng vệ tinh tương lai.

### 5.5 Tầng dữ liệu & đồng bộ với OSM — overlay vs full-mirror

Câu hỏi "sửa thẳng vào PBF cục bộ để thấy real-time mà vẫn sync OSM" có lời giải đã được thiết lập trong ngành — nhưng **không phải sửa file PBF** (PBF là snapshot bulk, không phải DB). Nạp PBF vào store sửa-được rồi sửa *store đó*.

Hai kiến trúc:

| | **A — Full mirror (nặng)** | **B — Overlay (lười, đề xuất phase 1)** |
|---|---|---|
| Store | DB schema-OSM cục bộ | PBF baseline (read-only) + lớp overlay edit |
| Sync OSM→local | replication phút/ngày, merge live | re-import PBF hằng ngày (nhịp tim) |
| Sync local→OSM | upload changeset + giải xung đột | push overlay khi duyệt, rồi PBF hấp thụ |
| Real-time | có (hai chiều) | **có** (dashboard render baseline+overlay) |
| Chi phí | = Editor Spatial DB (blocking #3) | ~5% của A |

**Cơ chế chuẩn, không phải tự chế:**
- **Nạp:** PBF → PostGIS bằng `osm2pgsql` là stack chính tắc (Bartoň, 2009).
- **Pull OSM→local:** replication diff của OSM, áp bằng `osm2pgsql --append`.
- **Push + phát hiện xung đột:** OSM dùng **version number per-element + optimistic locking** — *"Once a feature is edited, its version number is incremented… Changes are not explicitly stored in OSM but can be reconstructed by comparing subsequent versions"* (Juhász et al., 2020). Stale base → 409, phải re-merge. Đây đúng mô hình "first to commit wins" mà GIS versioned đa-người-dùng đã hình thức hóa (Bakalov, Hoel & Menon, 2009; Bakalov, Hoel & Heng, 2011).

**Vì sao overlay an toàn cho ca này:** xung đột đáng sợ là xung đột *hình học*. Phase-1 chỉ sửa **thuộc tính trên way sẵn có** — hai người hiếm khi tranh maxspeed cùng đoạn, re-base hằng ngày bắt được ca hiếm. Văn liệu collaborative-editing đồng thuận: phần đắt là **branch-and-merge tổng quát** ("conflict management is still delegated to users"). Overlay né hẳn merge engine → ~95% giá trị với ~5% chi phí.

**Quy tắc bất biến:** **OSM là source of truth; store cục bộ là bản làm việc, không bao giờ là master.** PBF hằng ngày là nhịp re-sync. Hệ quả: edit hôm nay chỉ hiện trong metric *của chính bạn* khi PBF mai re-import — **độ trễ 1 ngày**, vòng lặp đóng qua OSM chứ không qua PBF. Đừng kỳ vọng real-time hai chiều ở phase 1.

### 5.6 Pipeline biển báo (sau): dedup → định vị → liên kết đường

Mapillary cho **vị trí camera nơi *thấy* biển**, không phải vị trí biển. Cùng một biển vật lý xuất hiện ở N frame lệch khỏi đường. Công thức đã có tên trong văn liệu, 3 bước:

1. **Cluster** các detection của một biển — theo cả vị trí *và hướng*. Pedersen & Torp (2021) so 5 cách (DBSCAN → **Directional-DBSCAN**), đạt F1 0.889, sai số vị trí 5,1 m, sai số hướng ±11,4° — *"important to consider both the location and the direction, e.g., are you entering or leaving a 60 km/h zone."*
2. **Tam giác đạc vị trí** từ track camera, kết hợp **monocular depth estimation** (Krylov, Kenny & Dahyot, 2018 — độ chính xác ~2 m, xấp xỉ GPS một-tần-số) và **MRF fusion** khi có nhiều biển giống nhau (Krylov & Dahyot, 2018).
3. **Map-match** biển vào đoạn đường + hướng di chuyển nó điều chỉnh → suy `maxspeed` cho **đoạn đó, hướng đó**.

Đây là việc ML/hình học thật, đặt đúng ở "sau" — nhưng có recipe rõ ràng, không hand-wave.

---

## 6. Thiết kế dashboard (views)

Hệ có **hai mặt** (§5.4): (1) **scoreboard metrics** tại `dashboards/app_metrics.py` (Streamlit) — view tiến độ cho lãnh đạo, "ta đang làm thế nào", các tab dưới đây; (2) **lane visualizer** — buồng lái editor, "tôi sửa gì". Tab 4 nối hai mặt qua deeplink. Scoreboard thay/bổ sung `app_maxspeed.py`.

### Tab 1 — Tổng quan (Headline)

```
┌──────────────────────────────────────────────────────────┐
│  VN OSM Road Metrics          Last updated: 2026-06-18   │
│  ─────────────────────────────────────────────────────── │
│  Maxspeed  12.9%  ↑+0.01% hôm nay   133,771 km total    │
│  Name      66.8%  ↑+0.03% hôm nay                       │
│  Lanes      8.2%  ─ không đổi                            │
│  Signals    4,821 nút   Biển tốc độ (Mapillary): 18,432  │
└──────────────────────────────────────────────────────────┘
```

### Tab 2 — Xu hướng (Trend)

- Line chart: maxspeed% + name% + lanes% theo ngày (từ `history/*.json`)
- Chú thích sự kiện: ngày train editor, ngày SOP, scope pivot — dạng vertical marker
- Delta bar chart: km gained/lost mỗi ngày

### Tab 3 — Theo highway class

- Grouped bar chart: motorway / trunk / primary / secondary / tertiary × maxspeed% + name%
- Bảng số: km tổng, km có maxspeed, km có name, km có lanes

### Tab 4 — Theo quốc lộ (Road Worklist)

- Bảng xếp hạng các quốc lộ, sắp xếp theo `completeness_score` tăng dần (ưu tiên hoàn thiện trước)
- Cột: `ref` · `tên` · `centerline km` · `maxspeed%` · `name%` · `components` · `score`
- Filter: highway class, tỉnh, score threshold
- Click hàng → mở **lane visualizer** cho quốc lộ đó (deeplink) — editor xem schematic per-segment + bằng chứng street-view rồi stage edit (§5.4). *(Không deeplink tới `app_inspect.py` — module Streamlit in-dev này được thay bằng lane visualizer.)*

### Tab 5 — Theo tỉnh (Province Heatmap)

- Choropleth map: maxspeed% và name% per province (slider chọn attribute)
- Bảng hỗ trợ: tỉnh × maxspeed% × name% × total km

### Tab 6 — Biển báo (Signs)

- Mapillary sign points (từ `mapillary_sign_points.parquet`) — H3 hexmap
- Breakdown: speed / residential / no-overtaking / [placeholder cho 4 loại còn lại]
- Last pull date + coverage vs road network

---

## 7. Những gì cần xây mới

| Hạng mục | Loại | Độ phức tạp | OKR link |
|---|---|---|---|
| `province_maxspeed_coverage.py` | Script Python | Thấp (clone `province_name_coverage.py`) | O3KR1.1 |
| `history_append.py` | Script Python (~50 dòng) | Thấp | O3KR1.1 |
| Cron job / launchd plist | Infra | Rất thấp | O3KR1.1 |
| `dashboards/app_metrics.py` | Streamlit (6 tab) | Trung bình | O3KR1.1, O3KR3.3 |
| Signal count script | Script Python | Thấp (osmium filter `traffic_signals`) | O3KR1.1 |
| Completeness score logic | Python (~20 dòng) | Thấp | O3KR3.3 |

Tất cả đều là **thin wrappers trên data đã có** — không cần pipeline mới, không cần backend, không cần schema thay đổi. Ước tính tổng: 2–3 ngày công.

---

## 8. Những gì KHÔNG nằm trong scope (lần này)

- **Editor Spatial DB integration** — chờ schema chốt với Quân (blocking decision)
- **GSV / Google Street View** — chờ ngân sách
- **Turn restriction coverage** — cần script riêng, deferred
- **Address / house number coverage** — O3KR1.2 sub-ward layer chưa có
- **Real-time / sub-daily refresh** — Geofabrik chỉ daily, không cần sub-daily
- **User/contributor analytics** — không có OSM changeset pipeline

---

## 9. Câu hỏi mở

1. **Host ở đâu?** Dashboard Streamlit cần server chạy cron. Tùy chọn: VPS hiện có (Vultr, đang dùng cho TiTiler legacy) hoặc máy local có uptime ổn định. Chưa quyết định với Vũ/Huy (O4).
2. **Signals in/out T06?** Nếu in → cần thêm signal count script + Tab 6 mở rộng.
3. **Bao nhiêu lịch sử cần giữ?** Đề xuất: toàn bộ từ ngày bật cron — file history JSON nhỏ (~50 KB/ngày).
4. **Dashboard này có feed vào Editor Spatial DB không?** Logically yes — daily snapshot là input cho KR2 monitoring. §5.5 cho đường thoát phase-1: **overlay** không cần Editor DB; full-mirror mới = Editor DB (gắn blocking #3 + cột HITL §11.5).
5. **Editor sửa thẳng OSM hay stage-review?** §5.5/§11.6 khuyến nghị stage→review→push cho crowd part-time (tránh mass-revert theo mandate bằng-chứng); chỉ solo/trusted mới sửa thẳng.

---

## 10. Đề xuất trình tự thực hiện

```
Tuần 1
  Day 1: province_maxspeed_coverage.py + history_append.py + cron
  Day 2: app_metrics.py Tab 1+2+3 (headline + trend + class)
  Day 3: Tab 4 (road worklist) + completeness score

Tuần 2
  Day 1: Tab 5 (province choropleth)
  Day 2: Tab 6 (signs) + integration test toàn bộ pipeline
  Day 3: buffer / QA với MapOps team
```

Mỗi tab có thể ship độc lập — Tab 1+2 là giá trị cao nhất và có thể demo sau ngày 2.

---

## 11. Mô hình Human-in-the-Loop (HITL) — lộ trình tiến hóa

Dashboard + lane visualizer không chỉ là công cụ đo/sửa thủ công hôm nay; chúng là **tầng cổng (review gate)** mà về sau AI sẽ vận hành phía sau. Điểm mấu chốt: **hệ thống này đã là một hệ HITL — hiện đang để 100% thủ công.** Lên các nấc tự động hóa = **vặn một núm**, không phải xây lại. Cách đóng khung này khớp với nguyên tắc đã ghi trong repo (*"AI detects, rules/graph reason, manual review for conflicts"*, cite RoadTagger) và lộ trình **manual → SOP → AI** của scope pivot.

### 11.1 Thang trưởng thành (maturity ladder)

| Nấc | Ai quyết định | Người làm gì | Máy làm gì |
|---|---|---|---|
| **0 — Thủ công (nay)** | Người | Đọc street-view, gõ `maxspeed=80` | Chỉ hiện gap + bằng chứng |
| **1 — Thủ công có máy gợi ý** | Người | Xác nhận/sửa giá trị *điền sẵn* | Biển Mapillary + luật Thông tư 38 pre-fill gợi ý |
| **2 — Máy dẫn, người trên vòng lặp** | Máy (độ tin cao); người (phần còn lại) | Chỉ review các edit *bị flag / độ tin thấp* | Auto-apply edit độ tin cao, đẩy phần bất định vào hàng đợi |
| **3 — Tự động có kiểm toán** | Máy | Spot-audit + xử lý reverts/khiếu nại | Edit 24/7; người lấy mẫu QA |

Tầm nhìn "AI auto-edit 24/7" = **nấc 3**, đạt được bằng cách hạ dần ngưỡng auto-accept từng nấc, không phải viết lại kiến trúc.

### 11.2 Cơ chế: selection function + ngưỡng tin cậy

Ý tưởng "đẩy edit độ tin thấp cho người, auto-accept phần còn lại" có tên chính thức và nền tảng 55 năm: **selective classification / classification with reject option** (Chow, 1970). Một bộ phân loại được gắn thêm **selection function**: nếu độ tin < ngưỡng `t` thì *abstain* (đẩy cho người), ngược lại tự quyết — đánh đổi giữa **coverage** (tỷ lệ tự quyết) và **độ chính xác** (Pugnana & Ruggieri, 2023). Phiên bản "phần bị từ chối chuyển cho chuyên gia" gọi là **learning to defer / algorithmic triage** (Keswani, Lease & Kenthapadi, 2021): *"the classifier is expected to handle the primary load… the role of human experts is to provide assistance for input samples where the classifier cannot achieve reasonable confidence."*

Quan trọng cho maxspeed: **ngưỡng có thể đặt riêng theo loại tag** — Hanczar (2019): *"Different rejection thresholds can be fixed for each class if the seriousness of the different types of error is not equal."* → đặt ngưỡng **khắt khe hơn** cho edit rủi ro (hạ giới hạn tốc độ) so với edit an toàn.

### 11.3 Lợi thế riêng của maxspeed: hai nguồn độ tin độc lập

Một kết luận maxspeed có thể đến từ **hai đường độc lập**:
1. **Tri giác (AI đọc biển trong street-view)** — xác suất, cần bằng chứng.
2. **Luật (Thông tư 38: morphology → tốc độ mặc định)** — tất định, suy ra từ tag sẵn có.

Khi **cả hai khớp** → độ tin rất cao → auto-accept sớm (đạt nấc 2 nhanh cho nhóm này). Khi **mâu thuẫn** → đúng ca "manual review for conflicts", đẩy cho người. Vậy `wiki/` (ma trận quyết định Thông tư 38) không chỉ là tài liệu vận hành — nó là **rule engine cho phép nâng ngưỡng auto-accept an toàn** ở nơi luật tự quyết được.

### 11.4 Review queue = nhà máy nhãn huấn luyện (active learning)

Mỗi lần editor sửa giá trị máy điền sẵn, sửa đó là **một nhãn huấn luyện**. Cùng một review store vừa bảo vệ OSM vừa âm thầm dựng dataset huấn luyện model nấc 2 và bộ nhận diện biển **retrain cho VN** (thay bộ Âu-châu của Mapillary). Đây là **active learning**: ưu tiên gán nhãn các mẫu máy *bất định nhất*, không phải ngẫu nhiên (Yang, Drake & Damianou, 2018). Vòng lặp này **đo được**: Scalpel-CD (Yang, Smirnova & Yang, 2019) cải thiện chất lượng nhãn **12,9% chỉ với 2,8% mẫu được người kiểm** — công thủ công không phải chi phí chìm, nó là tài sản huấn luyện. HITL trên dữ liệu OSM noisy là paradigm chuẩn (Usmani, Bovolo & Napolitano, 2023).

### 11.5 Thay đổi nhỏ trong schema (cụ thể hóa cột confidence/provenance)

Văn liệu biến hai cột "confidence + provenance" thành các trường có tên, biện minh được:

| Trường trên mỗi staged edit | Thuật ngữ văn liệu | Mục đích |
|---|---|---|
| `confidence` (0–1) | selection-function score (Chow, 1970) | auto-accept vs defer |
| `accept_threshold` theo loại tag | per-class rejection threshold (Hanczar, 2019) | ngưỡng khắt khe hơn cho edit rủi ro |
| `source` (AI / rule / human) + `reviewer_decision` | learning-to-defer + active-learning label | cấp dữ liệu huấn luyện |

Đây là input cho quyết định **schema Editor Spatial DB** (blocking decision #3) — HITL giải thích *tại sao* các cột này tồn tại.

### 11.6 Lưu ý trung thực

Keswani et al. (2021) cảnh báo: defer cho người chỉ đúng khi người *đáng tin hơn* máy ở ca đó — với 20–30 editor part-time trình độ khác nhau thì không hiển nhiên (*"different human experts can have different prediction behaviours"*). Hệ quả: route edit bị defer cho **reviewer giỏi hơn**, và **giữ spot-audit cả trên edit đã được người duyệt**. Cổng người là một tầng chất lượng, không phải oracle tuyệt đối. Và HITL chính là thứ giữ bạn **không bị mass-revert** theo mandate bằng-chứng — cổng người là rào an toàn thường trực, không phải giàn giáo tháo bỏ ở nấc 3.

---

*Report này là thiết kế nội bộ. Cập nhật khi có thêm thông tin từ các video tham chiếu hoặc khi scope thay đổi. Các trích dẫn trong §2.4 được kiểm chứng qua scite (2026-06-18).*

---

## Tài liệu tham khảo

Almendros-Jiménez, J. M., & Becerra-Terón, A. (2018). Analyzing the tagging quality of the Spanish OpenStreetMap. *ISPRS International Journal of Geo-Information*, 7(8), 323. https://doi.org/10.3390/ijgi7080323

Bakalov, P., Hoel, E., & Menon, S. (2009). Versioning of network models in a multiuser environment. In *Advances in Spatial and Temporal Databases (SSTD 2009)* (pp. 6–24). Springer. https://doi.org/10.1007/978-3-642-02982-0_4

Bakalov, P., Hoel, E., & Heng, W.-L. (2011). Editing and versioning for high performance network models in a multiuser environment. *GeoInformatica*, 15(4), 769–803. https://doi.org/10.1007/s10707-011-0126-7

Barrington-Leigh, C., & Millard-Ball, A. (2017). The world's user-generated road map is more than 80% complete. *PLOS ONE*, 12(8), e0180698. https://doi.org/10.1371/journal.pone.0180698

Barron, C., Neis, P., & Zipf, A. (2013). A comprehensive framework for intrinsic OpenStreetMap quality analysis. *Transactions in GIS*, 18(6), 877–895. https://doi.org/10.1111/tgis.12073

Bartoň, R. (2009). Custom OpenStreetMap rendering – OpenTrackMap experience. *Geoinformatics FCE CTU*, 4, 5–28. https://doi.org/10.14311/gi.4.1

Bres, R., Peralta, V., & Le-Guilcher, A. (2023). Analysis of cycling network evolution in OpenStreetMap through a data quality prism. *AGILE GIScience Series*, 4, 1–9. https://doi.org/10.5194/agile-giss-4-3-2023

Chow, C. K. (1970). On optimum recognition error and reject tradeoff. *IEEE Transactions on Information Theory*, 16(1), 41–46. https://doi.org/10.1109/TIT.1970.1054406

El Rashidy, R. A. H., & Grant-Muller, S. (2019). A composite resilience index for road transport networks. *Proceedings of the Institution of Civil Engineers – Transport*, 172(3), 174–183. https://doi.org/10.1680/jtran.16.00139

Gatea, Z. K., & Al-Bakri, M. (2023). Measuring the attribute accuracy and completeness for the OpenStreetMap roads networks for two regions in Iraq. *Journal of Engineering*, 29(5), 156–168. https://doi.org/10.31026/j.eng.2023.05.12

Hanczar, B. (2019). Performance visualization spaces for classification with rejection option. *Pattern Recognition*, 96, 106984. https://doi.org/10.1016/j.patcog.2019.106984

Juhász, L., Novack, T., Hochmair, H. H., et al. (2020). Cartographic vandalism in the era of location-based games—The case of OpenStreetMap and Pokémon GO. *ISPRS International Journal of Geo-Information*, 9(4), 197. https://doi.org/10.3390/ijgi9040197

Keller, S., Gabriel, R., & Guth, J. (2020). Machine learning framework for the estimation of average speed in rural road networks with OpenStreetMap data. *ISPRS International Journal of Geo-Information*, 9(11), 638. https://doi.org/10.3390/ijgi9110638

Keswani, V., Lease, M., & Kenthapadi, K. (2021). Towards unbiased and accurate deferral to multiple experts. *arXiv*. https://doi.org/10.48550/arXiv.2102.13004

Krylov, V. A., Kenny, E., & Dahyot, R. (2018). Automatic discovery and geotagging of objects from street view imagery. *Remote Sensing*, 10(5), 661. https://doi.org/10.3390/rs10050661

Krylov, V. A., & Dahyot, R. (2018). Object geolocation using MRF based multi-sensor fusion. *2018 IEEE International Conference on Image Processing (ICIP)*, 2745–2749. https://doi.org/10.1109/ICIP.2018.8451458

Li, D., Gamage, M. M., & Cao, J. (2025). Mapping the completeness and positional accuracy of OpenStreetMap road data at the county level in the contiguous United States. *Transactions in GIS*, 29(4). https://doi.org/10.1111/tgis.70077

Nasiri, A., Abbaspour, R. A., & Chehreghan, A. (2018). Improving the quality of citizen contributed geodata through their historical contributions: The case of the road network in OpenStreetMap. *ISPRS International Journal of Geo-Information*, 7(7), 253. https://doi.org/10.3390/ijgi7070253

Pedersen, K. F., & Torp, K. (2021). Geolocating traffic signs using large imagery datasets. *Proceedings of the 17th International Symposium on Spatial and Temporal Databases (SSTD '21)*, 34–43. https://doi.org/10.1145/3469830.3470900

Pugnana, A., & Ruggieri, S. (2023). A model-agnostic heuristics for selective classification. *Proceedings of the AAAI Conference on Artificial Intelligence*, 37(8), 9461–9469. https://doi.org/10.1609/aaai.v37i8.26133

Usmani, M., Bovolo, F., & Napolitano, M. (2023). Remote sensing and deep learning to understand noisy OpenStreetMap. *Remote Sensing*, 15(18), 4639. https://doi.org/10.3390/rs15184639

Vierø, A. R., Vybornova, A., & Szell, M. (2024). How good is open bicycle network data? A countrywide case study of Denmark. *Geographical Analysis*, 57(1), 52–87. https://doi.org/10.1111/gean.12400

Yang, J., Drake, T., & Damianou, A. (2018). Leveraging crowdsourcing data for deep active learning — An application: Learning intents in Alexa. *Proceedings of the 2018 World Wide Web Conference (WWW '18)*, 23–32. https://doi.org/10.1145/3178876.3186033

Yang, J., Smirnova, A., & Yang, D. (2019). Scalpel-CD: Leveraging crowdsourcing and deep probabilistic modeling for debugging noisy training data. *Proceedings of the 2019 World Wide Web Conference (WWW '19)*, 2158–2168. https://doi.org/10.1145/3308558.3313599

Zhang, J., Mao, X., & Han, Q. (2024). Research on data quality evaluation method of OpenStreetMap road network: Taking Taiwan island as an example. *SPIE Proceedings*. https://doi.org/10.1117/12.3048788
