# Agenda — Review tối trước Present (09/06/2026)
> *Cập nhật 2026-06-09 · [🧭 Orchestrator](../README.md) · [Brief present](../leadership/2026-06-10-brief.md) · [OKR](../vision/okr-2026.06.md)*

**Khi nào:** tối Thứ Ba 09/06 · **Tham dự:** Anh (chủ trì), Tuệ, Quân, Vũ, Huy, Thiện
**Mục tiêu duy nhất:** ráp xong **file present board-ready cho T4 10/06** → mỗi module ra **1 slide** theo khung *Hiện trạng → Kế hoạch → Chi phí/Ask*, và **chốt các ô 🔲 còn trống** trong [brief §10](../leadership/2026-06-10-brief.md).
**Output cần có khi tan họp:** (1) thứ tự slide + chủ slide; (2) **1 con số ask tổng + 1 mốc thời gian**; (3) ai còn nợ số gì, hạn sáng T4.

---

## Khung thời gian (~90')

| # | Thời lượng | Nội dung | Chủ trì | Output |
|---|--:|---|---|---|
| 0 | 5' | Mục tiêu + nhắc khung slide chung + thứ tự present | Anh | Thống nhất khung |
| 1 | 8' | **Lớp tích hợp** (mở đầu deck): selling point → kiến trúc 1 hình → build-vs-buy | Anh + Tuệ | Slide mở đầu |
| 2 | 7' | **Enrichment** (maxspeed/biển/làn) — đã sẵn sàng | Tuệ | Slide §1 ✅ |
| 3 | 7' | **Routing & Traffic** (Valhalla, Mapillary profile, TomTom display) | Huy | Slide §2 + 🔲 cost TomTom |
| 4 | 7' | **POI / Search** (crawl Amazon/Grab+H3+OpenBuildings+TomTom) | Vũ | Slide §3 + 🔲 giá API |
| 5 | 5' | **Metrics & retention** (5 màn hình, Waze D7=22%) | Thiện | Slide §4 |
| 6 | 5' | **Map identity / UX** — **cần 1 mockup** cho board | Thiện + Tuệ | 1 ảnh mockup |
| 7 | 3' | **MapOps tooling** (editor + Mapbox Playground clone) | cross-team | Slide §6 (concept) |
| 8 | 7' | **Hạ tầng MAP_INFS** 0.1→0.5→2.0M; sizing peak/avg | Vũ + Huy | Slide O4 + 🔲 cost infra |
| 9 | 15' | **🔴 CHỐT ASK HỢP NHẤT** (mục dưới) | Anh | 1 số tổng + timeline |
| 10 | 10' | **Pass nói thẳng / rủi ro** — đo được vs đang dev vs TBD | Toàn team | Danh sách caveat |
| 11 | 8' | Phân công slide + ai nợ số gì (hạn sáng T4) | Anh | Bảng phân công |
| 12 | 3' | Lịch + xác nhận ai trình mục nào trước board | Anh | Chốt |

---

## Mục 9 — Chốt ASK hợp nhất (cái board phải quyết)

Điền cho xong [brief §10](../leadership/2026-06-10-brief.md). **Recording + OKR đều KHÔNG có số này → phải chốt tối nay:**

| Hạng mục | Cần ai | Trạng thái |
|---|---|---|
| **$/km² ảnh vệ tinh** (× 20,350 km²) | **Vũ** (UP42/Skywatch) | 🔲 |
| **Giá per-request** Amazon/Grab + TomTom (× volume MAU) | **Vũ** | 🔲 |
| **Cost hạ tầng** 0.5M/2.0M (thuê) | **Vũ + Huy** (sau họp SRE) | 🔲 |
| **Nhân lực review + incentive** crowdsource | **Anh / HR** | 🔲 |
| **AI tools** (~$200/người) + thiết bị (màn hình, máy training) | **Anh** | 🔲 |
| **Headcount** (5 JD đang mở) | **Phụng** | 🔲 |
| → **TỔNG capex + opex + timeline** | Anh ráp | 🔲 |

> Nếu một ô **không kịp có số thật** → present dạng **range hoặc "đang chốt giá"**, KHÔNG bịa số. Board thà thấy ô mở còn hơn số sai.

## Quyết định cần lock tối nay
1. **Thứ tự + người trình** từng mục trước board.
2. **Quy tắc trọng số** decision-tree maxspeed khi nguồn lệch (vd luật ×0.7) — đầu vào demo T-1 của Tuệ.
3. **1 mockup map** nào được chọn để show (identity).
4. UX reference = **Yandex** (Map/Nav/Go); API = **Mapbox** — chốt để slide thống nhất.

## Câu hỏi còn mở mang vào (từ [biên bản 08/06](./2026-06-08-team-sync.md))
- App analytics log ở đâu (AppsFlyer/GA — Thiện hỏi Data team).
- RAP có traffic tile để benchmark không (verify trước khi cam kết).
- Máy training: PC ~100tr vs DGX Spark vs Colab — chạy thử rồi tính.

---

## Biên bản thực tế — chốt từ recording (nguồn: [transcript đầy đủ](./2026-06-09-review-transcript.md))

> Buổi review thực tế chỉ có **Anh + Tuệ + Huy/Vũ**; bám sát recording. Những gì chốt:

**Phân công Tuệ (việc của mình):**
1. **Bảng street-name coverage + pipeline điền tên đường từ address.** % OSM way thiếu `name`; rồi từ dữ liệu địa chỉ/POI (chuỗi số nhà "14, 16 … ngõ 66 Trần Hưng Đạo") → build **vector đường** → *success* tên ứng viên (VN + EN) overlay lên way ID rỗng cho editor duyệt (kiểu Facebook Rapid; đúng method paper Amazon city-scale). Thêm **confidence layer** theo luật số lớn; **outlier** ("103 Trần Hưng Đạo" lọt giữa toàn "ngõ 66") → flag review. Độ dài vector address khuyến nghị **split way** (ngách 100 m ⇒ way ~100 m). **Tải thêm residential + service** (ngõ/hẻm HN-SG để class `service`) — phần lớn nhất. ✅ baseline đã có: tertiary+ = **50,469 km không tên** (đúng con số "50.000 km" Anh nói); residential không tên ≈ **347,000 km**.
2. **Maxspeed → model man-hour cost** trong dashboard: % cần review ⇒ man-hour ⇒ tiền ở **~30–40k/giờ** (cộng đồng/thường) hoặc **~100k/giờ** (MapOps pro); ưu tiên motorway.
3. **Dashboard satellite:** visualize/highlight ô H3 được chọn (click xem ảnh + phân phối); thêm **giá theo zoom** (zoom~20 = mua hi-res; zoom ≤16 dùng Sentinel ~10 m). Chốt slider: **0.1 × $12/km² ≈ $250k** (max), 0.3 ≈ $120k; hero buy ~20,000 km² ≈ **$160k ≈ 4–6 tỷ**.
4. **Street view:** **95 tài xế × 800 km/tháng × 2 tháng** (không phải 300×250); **1 ảnh + 1 GPS + 1 IMU / giây**; trả theo **tier phủ** (mới vs trùng; trước/sau/trái/phải) + hợp đồng & nghiệm thu điện tử; GPS/giây = speed profile ETA toàn quốc cho Huy.
5. **Demo T5:** tool split speed-limit + **rule trọng số** decision-tree (vd luật ×0.7 khi nguồn lệch).
6. Gửi Anh **template CSV Bmap cũ** (schema POI) — lấy từ máy mình, **không hỏi Phụng**.
7. Là **bên nhận hàng** từ MapOps → build **spec nghiệm thu** (contract input↔output).

**Khung do Anh chốt (cho present):**
- Tầm nhìn: **AI edit OSM 24/7, người chỉ duyệt** — mỗi *paper công nghiệp* (ĐH×công ty: MIT×Uber, Thanh Hoa×Baidu, Alibaba/KTH lane-level) → backlog kèm số chi phí/thời gian. Paper Baidu: **~95% speedup** nhờ record bước edit người rồi train agent replay.
- **Scope tới T9: chỉ speed-limit + lane-level ở ngã tư + ra/vào khu dân cư + tốc độ.** Maxheight/weight/width **hoãn T9→T12** (phase xe tải). Quân = lớp luật. Turn-restriction + thiếu đường đã có team QC/SM lo → **không phải việc mình**; hai gap không ai làm = **speed-limit + lane-level**.
- Mapillary crawl **hợp pháp** (account mới, chia schedule theo rate-limit). 4 mode bản đồ chốt: place-discovery · routing/fleet · planning/land-cover · **ảnh vệ tinh multi-date (= cục của Tuệ)**. Launch tháng này: lớp **ảnh vệ tinh mới nhất** là hero của CEO + map-type kiểu Google + approve kiểu Rapid trên mobile.

**🔲 → trạng thái ô ask:** sat ≈ **$250k (max)** đã có khung số; street-view = **95 driver × 800 km × 2 thg** + storage TB (đang tính); maxspeed review = **man-hour × 30–100k** (đang tính). Vẫn 🔲: giá API POI/TomTom, cost hạ tầng 0.5/2M, incentive crowdsource, headcount 5 JD.

---
*File này = biên bản 09/06; cập nhật 🔲 → ✅ trong [brief](../leadership/2026-06-10-brief.md) và [orchestrator](../README.md).*
