# Báo cáo công việc — Hệ thống Làm giàu Dữ liệu Giao thông OSM

**Người báo cáo:** Tuệ (Geospatial Data Analyst)
**Ngày:** 2026-06-07
**Trạng thái dự án:** Khởi động Phase 1 (Nền tảng)

---

## 1. Đã hoàn thành

### 1.1. Demo satellite tile server (đã hạ ưu tiên)
- Pipeline cơ bản: fetch ảnh vệ tinh theo thời gian → xử lý → deploy phục vụ dưới dạng
  **XYZ tile URL** dùng được trực tiếp trong OSM editor.
- **Quyết định:** *deprioritize* — chuyển trọng tâm sang hệ thống làm giàu dữ liệu OSM (3 bài
  toán: maxspeed, đèn tín hiệu, số làn).

### 1.2. Thư viện nghiên cứu nền tảng — 22 papers bình duyệt (scite-verified)
Đã tập hợp, xác minh và chú giải 22 nghiên cứu, nhóm theo 4 mảng. Chi tiết:
`osm-enrichment/research/README.md`; danh mục tham khảo đã chèn vào `PROJECT_PLAN.md`.

**Key insights:**

- **(i) Viễn thám & chất lượng dữ liệu** — Hướng ML + remote sensing để làm giàu/đánh giá OSM
  đã *trưởng thành*; kiến trúc **CNN (nhìn) + GNN (suy luận theo đồ thị)** là state-of-the-art cho
  suy luận thuộc tính đường (Vargas-Munoz 2021; Mo 2024). → Không cần phát minh lại, đi theo
  pattern đã được kiểm chứng.

- **(ii) Giới hạn tốc độ** — OSM *vốn dĩ* thiếu maxspeed; các engine định tuyến phải fallback về
  **bảng tốc độ mặc định theo luật của từng quốc gia** (chỉ ~24 nước được định nghĩa trên OSM Wiki —
  VN gần như chưa có) (Guth 2020). Trích xuất biển báo từ **Mapillary + OSM** đã có tiền lệ chạy được
  (Ajmar 2019). → Khẳng định chiến lược "luật làm xương sống, biển báo bổ sung".

- **(iii) Ngã tư có đèn tín hiệu** — Có pipeline *detect → geolocate → đặt lên bản đồ* cho vật thể
  ven đường từ ảnh đường phố (Zhang 2021), phát hiện đèn tín hiệu cho HD map (Mentasti 2023), và
  phân tích cấu trúc ngã tư từ **ảnh vệ tinh** làm phương án dự phòng khi thiếu ảnh đường phố
  (Wijnands 2020). → Đúng kiến trúc 3 bước trong plan.

- **(iv) Số làn (laning)** — Nguồn cốt lõi **RoadTagger (He 2020)**: bộ phân loại ảnh thuần (CNN)
  bị *giới hạn bản chất* (receptive field) cho việc đếm làn; thêm suy luận theo đồ thị nâng độ chính
  xác **đếm làn từ 71.8% → 77.2%** (giảm 22.2% sai số tuyệt đối). → Bằng chứng bình duyệt cho luận
  điểm "AI nhận diện — quy tắc kết luận" (thay cho nguồn "Nilsson 2024" không có trong kho bình duyệt).

### 1.3. Baseline mạng lưới đường + độ phủ maxspeed (tính trực tiếp từ OSM PBF)
- Tải bản trích xuất **Geofabrik Vietnam (2026-06-06)**, lọc highway tertiary+, tính **độ dài
  geodesic (WGS84)** theo từng class kèm độ phủ maxspeed.
- Pipeline tái lập được: `osm-enrichment/baseline/run.sh` (osmium + python/pyproj).

| Class | Tổng km | Có maxspeed | % |
|---|--:|--:|--:|
| motorway | 6,037 | 5,822 | 96.4% |
| trunk | 23,087 | 5,020 | 21.7% |
| primary | 17,539 | 3,123 | 17.8% |
| secondary | 30,415 | 2,130 | 7.0% |
| tertiary | 56,694 | 1,178 | 2.1% |
| **Tertiary+ (tổng)** | **133,771** | **17,273** | **12.9%** |

**Key insight:** Toàn mạng tertiary+ ≈ **133,771 km**, nhưng **chỉ 12.9% có maxspeed → 87.1%
(~116,500 km) đang trống.** Cao tốc gần đủ (96%) nhưng càng xuống thấp càng trống; **tertiary chỉ
2.1%** mà lại là phần dài nhất. → Đây là vùng tạo giá trị lớn nhất cho Bài toán 1, và là mốc "trước"
để đo KPI làm giàu dữ liệu.

---

## 2. Đang vướng (Blocker)

- **Đăng ký tài khoản dịch vụ bị chặn do phụ thuộc email công ty.** Các mục *bắt buộc* của Phase 1 —
  **Mapillary API** và **Google Earth Engine** — yêu cầu đăng ký bằng email tổ chức / cần phê duyệt
  admin, hiện chưa truy cập được.
- **Tác động:** chặn Method 2 của Bài toán 1 (đọc biển báo Mapillary) và nguồn ảnh vệ tinh cho Bài
  toán 2 & 3. Phần dùng dữ liệu OSM thuần (như baseline mục 1.3) vẫn chạy bình thường.
- **Cần:** cấp email công ty / quyền tạo app Mapillary + tài khoản GEE (ưu tiên xử lý trong tuần để
  không trượt tiến độ Phase 1).

---

## 3. Kế hoạch tiếp theo

**Việc chạy được ngay (không phụ thuộc blocker — chỉ cần OSM):**
1. Tách độ phủ maxspeed **theo từng tỉnh/thành** → chọn quận/huyện pilot (Phase 4) dựa trên dữ liệu.
2. Đo riêng **maxspeed theo loại phương tiện** (`maxspeed:hgv`, `maxspeed:motorcycle`…) — trọng tâm
   thực sự của Bài toán 1.
3. Mở rộng baseline sang **đèn tín hiệu** (`highway=traffic_signals`) và **số làn** (`lanes`) để có
   bộ KPI "trước" đầy đủ cho cả 3 bài toán.
4. Số hóa bảng tốc độ luật VN (Thông tư 38/2021, NĐ 100/2019) thành bảng tra máy đọc.

**Khi hết blocker:**
5. Tạo app Mapillary API → đánh giá phạm vi phủ sóng tại Hà Nội / HCM.
6. Tạo & phê duyệt tài khoản GEE.

### Đề xuất: Dashboard quản lý làm giàu dữ liệu
Đề xuất xây một **dashboard** làm trung tâm điều phối — gộp 2 mục "Nên có" trong plan (bảng điều
khiển kiểm duyệt + báo cáo chất lượng định kỳ) thành một công cụ:

- **v0 — Baseline & KPI tracking:** độ phủ maxspeed / đèn tín hiệu / số làn theo **tỉnh** và theo
  **thời gian** (refresh từ PBF mới). Biến mục 1.3 thành sản phẩm sống thay vì báo cáo tĩnh.
- **v1 — Review queue:** hàng chờ các trường hợp mâu thuẫn (biển báo ≠ luật) để reviewer xử lý thủ
  công trước khi đẩy lên OSM.
- **v2 — Coverage map:** bản đồ tô màu đoạn đường đã/chưa có dữ liệu, phục vụ điều phối thu thập.

→ Đề xuất chốt dashboard v0 làm deliverable tiếp theo: chi phí thấp (dữ liệu đã có từ pipeline OSM),
chạy được ngay *bất chấp blocker tài khoản*, và cho lãnh đạo thấy tiến độ KPI rõ ràng.

---

*Phụ lục: số liệu máy đọc tại `osm-enrichment/baseline/maxspeed_coverage_result.json`;
thư mục dự án `osm-enrichment/` (PROJECT_PLAN, research/, baseline/).*
