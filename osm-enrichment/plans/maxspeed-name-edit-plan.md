# Kế hoạch triển khai — Edit Maxspeed & Name Tags

> Nguồn: `draft_plan_update_maxspeed_name_OSM.pdf` · Transcribe sang Markdown.
> **Thời gian:** 5 tháng · **17 Operators** · **Tổng ngân sách: 680.000.000 VND** · Ngày lập: 11/06/2026

---

## 1. Tổng quan dự án

Dự án triển khai đội ngũ operator để verify và edit trực tiếp trên OpenStreetMap các way thuộc Vietnam đang thiếu tag `maxspeed` và/hoặc `name`. Dữ liệu maxspeed chính xác là yêu cầu bắt buộc để **Valhalla** routing engine tính toán thời gian di chuyển đúng.

**Phạm vi:** Tất cả highway từ **motorway đến tertiary** (bao gồm link variants) — tổng cộng **131.976 ways / 118.570 km**.

Các highway loại `residential`, `service`, `unclassified`, `living_street` (**517.000+ km**) sẽ sử dụng **osm-legal-default-speeds** dựa trên Thông tư 38/2024/TT-BGTVT thay vì edit thủ công (build tool automate update).

---

## 2. Hiện trạng dữ liệu thiếu tag

### 2.1 P0 — Motorway, Trunk, Primary (+ links)

| Highway | Ways | Tổng km | Thiếu maxspeed | Km thiếu maxspeed | Thiếu name | Km thiếu name |
|---|--:|--:|--:|--:|--:|--:|
| motorway | 335 | 221.8 | 334 | 221.6 | 35 | 8.1 |
| motorway_link | 2.060 | 612.5 | 1.723 | 496.5 | 1.120 | 315.9 |
| trunk | 15.427 | 18.094,7 | 15.392 | 18.090,7 | 782 | 94.4 |
| trunk_link | 5.051 | 273.3 | 4.836 | 251.6 | 4.648 | 226.3 |
| primary | 16.709 | 14.476,5 | 16.676 | 14.468,4 | 1.581 | 540.3 |
| primary_link | 5.231 | 204.5 | 5.158 | 201.3 | 4.843 | 179.6 |
| **Tổng P0** | **44.813** | **33.883,3** | **44.119** | **33.730,1** | **13.009** | **1.364,6** |

### 2.2 P1 — Secondary, Tertiary (+ links)

| Highway | Ways | Tổng km | Thiếu maxspeed | Km thiếu maxspeed | Thiếu name | Km thiếu name |
|---|--:|--:|--:|--:|--:|--:|
| secondary | 28.712 | 28.493,3 | 28.551 | 28.335,5 | 4.376 | 3.884,1 |
| secondary_link | 4.106 | 167.5 | 4.068 | 166.1 | 3.838 | 151.6 |
| tertiary | 51.742 | 55.845,9 | 51.439 | 55.615,1 | 31.121 | 40.669,0 |
| tertiary_link | 2.603 | 180.2 | 2.581 | 177.1 | 2.474 | 167.5 |
| **Tổng P1** | **87.163** | **84.686,9** | **86.639** | **84.293,8** | **41.809** | **44.872,2** |

---

## 3. Kế hoạch nhân sự & ngân sách

| Nhóm | Km cần làm | Số người | Km/người/tháng | Km/người/giờ | Chi phí (VND) |
|---|--:|--:|--:|--:|--:|
| P0 — Motorway→Primary | 33.883 | 5 | 1.355 | 8.5 | 200.000.000 |
| P1 — Secondary→Tertiary | 84.687 | 12 | 1.411 | 8.8 | 480.000.000 |
| **TỔNG CỘNG** | **118.570** | **17** | **1.395** | **—** | **680.000.000** |

---

## 4. Timeline triển khai (5 tháng)

| Nhóm | Tháng 1 | Tháng 2 | Tháng 3 | Tháng 4 | Tháng 5 |
|---|---|---|---|---|---|
| **P0 — 5 người** | Motorway ~6.777 km | Trunk ~6.777 km | Trunk ~6.777 km | Primary ~6.777 km | Primary + Links ~6.777 km |
| **P1 — 12 người** | Secondary ~16.937 km | Secondary ~16.937 km | Tertiary ~16.937 km | Tertiary ~16.937 km | Tertiary + Links ~16.937 km |
| **KPI/tháng** | ~23.714 km | ~23.714 km | ~23.714 km | ~23.714 km | ~23.714 km |

---

## 5. Quy trình làm việc cho Operator

Mỗi operator sẽ được giao file chứa danh sách way ID cần edit, thực hiện theo quy trình:

1. **Bước 1:** Chọn từng way id được phân công.
2. **Bước 2:** Kiểm tra trên Street View / ảnh vệ tinh — xác định morphology đường (oneway, lanes, dual carriageway).
3. **Bước 3:** Xác định khu vực đông dân cư (urban) hay ngoài khu vực đông dân cư (rural).
4. **Bước 4:** Tra bảng tốc độ theo Thông tư 38/2024/TT-BGTVT (Điều 6–11).
5. **Bước 5:** Edit tag `maxspeed` và/hoặc `name` trên iD Editor.
6. **Bước 6:** Đánh dấu hoàn thành trong tracking sheet, note changeset.

> Tham chiếu bảng tra cứu: [Bộ Wiki Luật Internal](../wiki/01-bo-wiki-luat-internal.md) và [Bảng Quyết Định theo Luật](../wiki/02-bang-quyet-dinh-theo-luat.md).

---

## 6. KPI & Tracking

- **KPI trung bình:** ~1.395 km/người/tháng (~69.7 km/người/ngày).
- **Tracking:** Mỗi operator báo cáo số way đã edit + tổng km hàng tuần.
- **QA:** Random check 5–10% way đã edit để đảm bảo chất lượng.
- **Tool hỗ trợ:** File CSV đã bao gồm `way_id`, highway type, tags hiện có, link OSM, tọa độ, và độ dài (km).

---

## 7. Các giả định

| Thông số | Giá trị |
|---|---|
| Giờ làm việc | 8 giờ/ngày × 5 ngày/tuần × 4 tuần = 160 giờ/tháng |
| Lương operator | 8.000.000 VND/tháng/người |
| Thời gian dự án | 3 tháng *(xem ghi chú bên dưới)* |
| Năng suất P0 (motorway→primary) | ~8.5 km/giờ (~1.355 km/tháng/người) |
| Năng suất P1 (secondary→tertiary) | ~8.8 km/giờ (~1.411 km/tháng/người) |
| Buffer dự phòng | ~40% so với ước tính gốc 3 tháng — cho learning curve, Street View gaps, QA rework, nghỉ phép |
| Scope | Chỉ highway motorway → tertiary (+ link variants) |
| Ngoài scope | residential, service, unclassified, living_street → dùng osm-legal-default-speeds |
| Nguồn dữ liệu | Geofabrik `vietnam-latest.osm.pbf` (324 MB) |
| Tổng way cần edit | 131.976 ways / 118.570 km |

> **Ghi chú transcribe:** Bản gốc có điểm chưa nhất quán — tiêu đề + timeline ghi **5 tháng**, nhưng bảng giả định §7 ghi "Thời gian dự án: 3 tháng" (với buffer ~40% so với ước tính gốc 3 tháng). Cần chốt lại con số chính thức khi cập nhật bản kế tiếp.
