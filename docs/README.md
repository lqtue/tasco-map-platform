# 🧭 TASCO Mapping — Orchestrator (master index)

> **Cập nhật:** 2026-06-09 · **Người giữ:** Tuệ · **Chu kỳ:** OKR 2026.06
>
> File **điều phối duy nhất**: north star → OKR → workstream → trạng thái → link mọi tài liệu. Bắt đầu ở đây. Khi nghi ngờ một việc có đáng làm: quy chiếu về [North Star](./vision/tasco-mobility-platform.md).

## 0 · Mốc nóng

| Khi nào | Việc | Ai |
|---|---|---|
| **Tối T3 09/06** | [Review toàn report](./meeting-minutes/2026-06-09-review-agenda.md) → Anh ráp file present | Toàn team |
| **T4 10/06** | **Present ban lãnh đạo** (chủ tịch + CEO + chủ tịch cty con) | Anh Phụng |
| **T5 11/06** | Demo tool speed-limit (T-1); file data địa chỉ (H-2, T-6) | Tuệ; Vũ+Huy |

## 1 · North Star → OKR

- 🎯 **[North Star — TASCO Mobility Platform](./vision/tasco-mobility-platform.md)**: nền tảng bản đồ + mobility quốc gia; 4 định hướng (cộng đồng / doanh nghiệp / chính phủ / O2O), 10 lĩnh vực mở rộng.
- 📋 **[OKR 2026.06 (chính thức)](./vision/okr-2026.06.md)**: O1 ứng dụng người dùng · O3 biên tập/vận hành dữ liệu · O4 hạ tầng. Stack chốt: **MapLibre · Martin · Valhalla · Editor/Serving Spatial DB**. Scale **MAP_INFS 0.1M→0.5M→2.0M** (= 500K→2M MAU).

## 2 · OKR ↔ Workstream ↔ Owner ↔ Trạng thái

| OKR | Workstream | Owner | Trạng thái (2026-06-09) |
|---|---|---|---|
| O3KR1.1 | **Enrichment** (maxspeed/biển báo/làn) | **Tuệ** + Quân | 🟢 Baseline đo xong; dashboard live; demo T5 |
| O3KR1.2 / O1KR4–5 | **POI / Geocoding / Search** | Vũ + Huy | 🟡 Kiến trúc rõ; chưa có số/giá |
| O1KR3 / O3KR2 | **Routing & Traffic** | Huy + Vũ | 🟡 Valhalla + Mapillary speed profile; TomTom display-only |
| O1KR1,3 | **App UX / Design** (Yandex-ref) | Thiện (+Tuệ T-5) | 🟡 Figma design system; cần mockup |
| O3KR2,3 | **MapOps tooling / Editor** | cross-team | 🔴 Concept (editor + Mapbox-Playground clone) |
| Metric SP | **Product metrics / retention** | Thiện | 🟡 File 5-màn-hình; Waze D7=22% |
| O4 | **Hạ tầng MAP_INFS** | Vũ + Huy | 🟡 Sizing 0.1→0.5→2.0M; họp SRE T4 |

## 3 · Trạng thái chi tiết workstream

**🟢 Enrichment (Tuệ).** tertiary+ = 133,771 km, **chỉ 12.9% có maxspeed** → thiếu 116,498 km. Lấp: lớp luật (Quân, ~100%, $0 ngoài) + ảnh verify. Sat buy-envelope **20,350 km²**. Street view ~2 tháng/~15 TB. Dashboard: `../osm-enrichment/dashboard/app.py`. → [data-scope](./leadership/2026-06-10-data-scope.md), [brief](./leadership/2026-06-10-brief.md).

**🟡 POI/Search (Vũ).** Acquisition = **crawl + dedup đa nguồn**: Amazon Location (**provider Grab**) + Uber H3 + Google Open Buildings + TomTom. API clone **Mapbox**. ⚠️ **Recording không nêu giá** — opex per-request, TBD.

**🟡 Routing/Traffic (Huy).** Valhalla + historical speed profile từ **GPS công khai Mapillary** (tách moto/ô tô). TomTom = **display-only, không ETA** (~$8/1k cache). Benchmark ~10k OD/ngày vs RAP/Google.

**🟡 UX/Design (Thiện+Tuệ).** Figma design system clone **Yandex** (Map/Nav/Go); sync designer V.ETC + Tasco web map. Tuệ T-5: bộ icon đặc trưng + **1 mockup** cho present.

**🔴 MapOps tooling.** Editor visual (lane+speed+biển, kiểu Mapbox traffic-sign layer) + site test clone **Mapbox API Playground**. Mô hình: *AI proposes → MapOps verifies → Eng publishes → Product monitors*.

**🟡 Metrics (Thiện).** 5 màn hình (open/search/route-review/nav/community); retention D1/D7/D30; Waze D7=22% (nguồn industry).

**🟡 Hạ tầng (Vũ+Huy).** RPS peak/avg (kinh nghiệm Ahamove/Be); MAP_INFS 0.1→0.5→2.0M; họp SRE/backend T4.

## 4 · Acquisition dữ liệu (đã đính chính theo recording)

| Lớp | Nguồn (thực tế) | Mô hình | Giá |
|---|---|---|---|
| Maxspeed/biển | luật VN + Mapillary/Google SV + ảnh vệ tinh | build + verify | $0 ngoài (+ sat buy) |
| POI/địa chỉ | Amazon Location(**Grab**)+H3+Google Open Buildings+TomTom | crawl + dedup | per-request, **TBD** |
| Traffic | **Mapillary GPS công khai** + TomTom(display) | free + cache | TomTom ~$8/1k |
| Ảnh vệ tinh | UP42/Skywatch | **buy** (tương lai) | 20,350 km² × $/km² **TBD** |
| Base | OSM (daily) + Overture | free | $0 |

⚠️ **Recording 2 buổi họp KHÔNG nêu con số giá/ngân sách/headcount nào** — mọi $ trong các doc là minh hoạ, chờ Vũ (giá API/sat) + Anh/HR (review+incentive) điền. Chi tiết: [data-acquisition memory] & [brief §10](./leadership/2026-06-10-brief.md).

## 5 · Chỉ mục tài liệu

**Vision & OKR** → [`vision/`](./vision/)
- [tasco-mobility-platform.md](./vision/tasco-mobility-platform.md) · [okr-2026.06.md](./vision/okr-2026.06.md) (+ pdf, png)

**Leadership present (10/06)** → [`leadership/`](./leadership/)
- [2026-06-10-brief.md](./leadership/2026-06-10-brief.md) — deck 6 module + ask hợp nhất
- [2026-06-10-data-scope.md](./leadership/2026-06-10-data-scope.md) — scope enrichment (have/missing/cost)

**Biên bản họp** → [`meeting-minutes/`](./meeting-minutes/)
- [2026-06-05](./meeting-minutes/2026-06-05-team-sync.md) · [2026-06-08](./meeting-minutes/2026-06-08-team-sync.md) · [research-todos](./meeting-minutes/2026-06-08-research-todos.md) (bib scite + papers Phụng gửi) · [**2026-06-09 biên bản review**](./meeting-minutes/2026-06-09-review-agenda.md) (+ [transcript recording](./meeting-minutes/2026-06-09-review-transcript.md))

**Tuyển dụng / cấu trúc team** → [`team_recruit_job_description/`](./team_recruit_job_description/) (5 JD: Map Scientist, Data Scientist, MapOps Nav/POI, SW Eng)

**Lưu trữ (satellite tile — deprioritized)** → [`archive/`](./archive/)

**Code & module** (ngoài docs/): [`../osm-enrichment/`](../osm-enrichment/) (enrichment + baseline + dashboard + research) · [`../coverage/`](../coverage/) (H3 imagery planner) · [`../CLAUDE.md`](../CLAUDE.md) (chỉ dẫn repo)

## 6 · Số liệu chốt (verified)

- **Công ty:** HUT/HNX, est.1971, ~10k nhân viên, 88 cty con. VETC: **75% ETC, 4.2M chủ xe, 2M giao dịch/ngày**. Tasco Auto 14.8%. Partner: Geely/Mitsui/IFC.
- **Maxspeed:** 133,771 km tertiary+, 12.9% có → thiếu **116,498 km** (OSM 2026-06-06).
- **Sat envelope:** **20,350 km²** union (đô thị 15,355 + đường 5,662 + đảo 867, trừ trùng).
- **Validation:** AMap 2026 (lane-level từ crowdsource+satellite, >1M km) · RoadTagger 2020.

## 7 · Nguồn sự thật & cách verify

- **Recording họp** → NotebookLM skill (`~/.claude/skills/notebooklm`), notebook `c91ccfea…`. *Lưu ý: tool đang trả 1 summary cố định bất kể câu hỏi → chưa rút được OKR/giá chi tiết; OKR lấy từ [PDF chính thức](./vision/okr-2026.06.pdf).*
- **Paper** → scite MCP (verify trước khi cite).
- **Maxspeed/sat số** → reproduce: `../osm-enrichment/baseline/run.sh`, `../osm-enrichment/dashboard/`.
