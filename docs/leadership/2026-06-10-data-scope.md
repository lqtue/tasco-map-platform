# Data Scope & Acquisition — input cho present lãnh đạo (10/06)
> *Cập nhật 2026-06-09 · [🧭 Orchestrator](../README.md) · [North Star](../vision/tasco-mobility-platform.md) · [Brief đầy đủ](./2026-06-10-brief.md)*

**Người chuẩn bị:** Tuệ · **Cho:** anh Phụng present · **Nguồn số:** `osm-enrichment/baseline/maxspeed_coverage_result.json` (OSM extract 2026-06-06) + `coverage/data/cells.parquet`.

Khung Anh cần cho deck = với **mỗi loại dữ liệu**: *đang có gì → thiếu gì → quy mô/giá để lấp*. Phần của Tuệ = **quy mô (scope)**; ô giá ngoài (sat $/km²) để Vũ/procurement điền.

---

## 1. Maxspeed (dữ liệu giao thông) — đã đo xong

| Class | Tổng km | Có maxspeed | Thiếu | % thiếu |
|---|--:|--:|--:|--:|
| motorway | 6,037 | 5,822 | **215** | 3.6% |
| trunk | 23,087 | 5,020 | **18,067** | 78.3% |
| primary | 17,539 | 3,123 | **14,415** | 82.2% |
| secondary | 30,415 | 2,130 | **28,285** | 93.0% |
| tertiary | 56,693 | 1,178 | **55,516** | 97.9% |
| **TERTIARY+** | **133,771** | **17,273** | **116,498** | **87.1%** |

**Headline:** mạng tertiary+ ≈ 133,771 km; chỉ **12.9% có maxspeed** → **thiếu 116,498 km (87.1%)**. Cao tốc gần như xong (96.4%); vấn đề nằm ở trunk→tertiary.

**Cách lấp & chi phí lấy dữ liệu:**
- **Lớp luật (Quân)** gán được *candidate maxspeed* cho gần **100%** km thiếu, **chi phí ngoài = $0** (suy từ OSM + luật VN). Đây là phần lấp nhanh & rẻ nhất.
- **Lớp ảnh (Mapillary/street view)** chỉ cần để **verify + xử lý ngoại lệ** (đường có biển khác default, đường 1-line-2-làn). Đây là lý do cần chiến dịch street view (mục 3).
- Chi phí thực của maxspeed = **compute + nhân lực review**, không phải mua dữ liệu.

---

## 2. Ảnh vệ tinh — diện tích cần mua

Buy-envelope tính từ H3 (res 10) quanh 3 mục tiêu: đô thị + hành lang đường + đảo.

| Tiêu chí | km² |
|---|--:|
| Đô thị (built-up ≥ 10%) | 15,355 |
| Hành lang đường vận hành (motorway/trunk/primary) | 5,662 |
| Đường đang xây | 381 |
| Đảo (đất thật, OSM coastline) | 867 |
| **UNION (tổng cần mua, đã trừ trùng)** | **≈ 20,350 km²** |

> Tham chiếu: full Việt Nam ≈ 331,000 km² → mình **chỉ mua ~6%** diện tích nhờ lọc sparse quanh mục tiêu. Vùng đảo nếu tính cả mặt biển trong ranh đặc khu sẽ phình lên ~6,370 km² (Trường Sa toàn nước) — dùng **867 km² đất thật** mới trung thực.

**Giá = 20,350 km² × $/km²** (ô $/km² cần Vũ/procurement chốt theo UP42/Skywatch). Minh hoạ để leadership thấy độ nhạy:

| $/km² (cần xác nhận) | Tổng |
|---|--:|
| $3 (archive optical) | ~$61K |
| $8 | ~$163K |
| $15 (tasking sub-meter) | ~$305K |

→ **Cần Vũ điền giá thực.** Lưu ý hành lang đường (6,043 km²) trùng vùng cần maxspeed → ưu tiên mua phần này trước nếu cắt ngân sách.

---

## 3. Street view — thời gian phủ + storage

**Mô hình** (giả định ghi rõ để leadership chỉnh): overlap re-drive **×1.3**; dung lượng **~100 MB/km** (capture ~720p, 1 ảnh/5 m hoặc video dashcam); chia phase theo độ ưu tiên.

| Phase | Km lái 1 lần | Storage | ~300 tài xế @250km/th | ~500 @350 | ~800 @500 |
|---|--:|--:|--:|--:|--:|
| **P1** motorway+trunk+primary | 32,697 | ~4.3 TB | 0.6 th | 0.2 th | 0.1 th |
| **P2** + secondary | 60,982 | ~7.9 TB | 1.1 th | 0.5 th | 0.2 th |
| **P3** full tertiary+ | 116,498 | ~15.1 TB | **2.0 th** | 0.9 th | 0.4 th |
| P3 + residential (~×2.5) | ~291k | ~37.9 TB | 5.0 th | 2.2 th | 0.9 th |

**Đọc cho leadership:**
- Phủ **tertiary+ toàn quốc ≈ 2 tháng** với ~300 tài xế tích cực (≈30% trong ~1,000 nhân viên có ô tô) — khớp ước tính ~2 tháng của Anh.
- Bắt đầu **P1 (trunk+primary, ~33k km)** xong trong **vài tuần**, ~4 TB — đây là phần giá trị cao nhất (đè lên đúng đoạn thiếu maxspeed quan trọng).
- Chi phí street view = **internal**: storage (~15 TB cho tertiary+) + incentive KPI/Loyalty + compute chạy model detect biển. **Không mua dữ liệu ngoài.**
- Lợi thế độc quyền Anh nhấn: ~10–12k nhân viên khắp nước → phủ được vùng mà Grab/Google chỉ có HN+HCM.

---

## Tổng cho deck (1 dòng/dữ liệu)

| Dữ liệu | Đang có | Thiếu | Lấp bằng | Chi phí |
|---|---|---|---|---|
| **Maxspeed** | 17,273 km (12.9%) | **116,498 km** | Luật (≈100%, $0) + ảnh verify | Compute + review |
| **Ảnh vệ tinh** | 0 mua | **20,350 km²** cần mua | UP42/Skywatch | 20,350 × $/km² *(Vũ điền)* |
| **Street view** | 0 | ~33k km (P1) → 116k km (tertiary+) | Crowdsource nội bộ | ~4–15 TB + incentive, **$0 ngoài** |

## Ô cần người khác điền trước Wed
- **$/km² ảnh vệ tinh** → Vũ / procurement (UP42/Skywatch).
- **Giá nhân lực review maxspeed + incentive street view** → Anh / HR.
- *(Storage TB ở trên là phần Tuệ chịu, đã có.)*

---
*Reproduce: `osm-enrichment/baseline/run.sh` cho maxspeed; query `coverage/data/cells.parquet` cho km² (script trong lịch sử chat). Street-view = mô hình tham số, chỉnh overlap/MB-per-km/tài xế để ra lại bảng.*
