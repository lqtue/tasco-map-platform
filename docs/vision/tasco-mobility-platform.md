# TASCO Mobility Platform — North Star

> **Cập nhật:** 2026-06-09 · **Nguồn:** slide chiến lược "TASCO MOBILITY PLATFORM" ([ảnh gốc](./tasco-mobility-platform.png)) · OKR chi tiết: [okr-2026.06.md](./okr-2026.06.md) · Quay lại [orchestrator](../README.md)
>
> Đây là **mục tiêu tối thượng (north star)** mà mọi đầu việc trong repo phải quy chiếu về. Khi không chắc một task có đáng làm không → kiểm tra nó phục vụ định hướng/lĩnh vực nào dưới đây.

## MỤC TIÊU

Xây dựng **nền tảng bản đồ và mobility quy mô quốc gia cho Việt Nam**, từng bước hình thành **hạ tầng dữ liệu không gian và giao thông** phục vụ **người dân, doanh nghiệp và cơ quan quản lý nhà nước**.

## ĐỊNH HƯỚNG PHÁT TRIỂN (4 hướng)

1. **Phục vụ cộng đồng** — cung cấp **miễn phí** dịch vụ bản đồ, tìm kiếm vị trí và dẫn đường cho người dùng cá nhân.
2. **Hỗ trợ doanh nghiệp** — vận hành **phi lợi nhuận** với tổ chức/doanh nghiệp giao thông – logistics, thu phí dịch vụ hợp lý để duy trì hạ tầng nền; **giúp vận tải nội địa giảm phụ thuộc nền tảng bản đồ nước ngoài**.
3. **Đồng hành cùng Chính phủ** — hạ tầng số bản đồ phục vụ quản lý giao thông, an toàn giao thông, đô thị thông minh; **làm chủ Mobility Data quốc gia**.
4. **Chuyển đổi số toàn diện (O2O)** — nền tảng hợp nhất **Mobility + AI + Commerce** (Online-to-Offline); tích hợp sâu thanh toán, bảo hiểm, chuỗi cung ứng, dịch vụ ngành xe → hệ sinh thái giao dịch số xoay quanh hành trình người dùng và chu kỳ vận hành phương tiện.

## CÁC LĨNH VỰC MỞ RỘNG (10)

| # | Lĩnh vực | Nội dung cốt lõi |
|---|---|---|
| 1 | **Hạ tầng Tiện ích đường bộ** | Kết nối bãi đỗ + hạ tầng năng lượng (xăng/dầu/điện) + **ETC thu phí không dừng** xuyên suốt hành trình; kèm **chỉ dẫn / cảnh báo** an toàn giao thông. |
| 2 | **Hệ sinh thái Quảng cáo & Thương mại số** | Local Search, **Indoor Navigation**, Location-based Advertising, Digital Commerce (mô hình Google Maps/Ads) gắn với hạ tầng di chuyển + dịch vụ tại ga/TTTM + SaaS cho SME. |
| 3 | **Tài chính & Bảo hiểm chuyên ngành** | Dịch vụ tài chính/ngân hàng/bảo hiểm thiết kế theo **hành vi vận hành xe** và hành trình. |
| 4 | **Chuỗi cung ứng dịch vụ xe** | Đặt & tối ưu sửa chữa, cứu hộ với mạng xưởng/gara + nguồn phụ tùng. |
| 5 | **Hợp tác cơ quan quản lý** | Hướng dẫn/cảnh báo tuân thủ + an toàn; **thu hộ phí đường bộ**: phạt vi phạm, dừng đỗ lòng đường, phí nội đô. |
| 6 | **Di chuyển hành khách** | Mobility toàn diện cho vận tải hành khách, xe dịch vụ, đội xe DN; quản lý phương tiện, tối ưu trạm sạc, điều phối bản đồ + tài chính đầu tư phương tiện. |
| 7 | **Logistics & Giao vận** | Tối ưu vận tải hàng + **last-mile**; điều phối thông minh + traffic real-time + hệ dịch vụ kỹ thuật phương tiện. |
| 8 | **HD Maps & ADAS Maps cho Xe thông minh** | Bản đồ độ phân giải cao + ADAS; định vị nền tảng thành **giải pháp nhúng gốc (OEM)** trong hệ điều hành xe phân phối tại VN. |
| 9 | **Bản đồ đường thủy nội địa & biển đảo** | Mở rộng dữ liệu không gian sang giao thông thủy nội địa + hải đảo. |
| 10 | **Bản đồ Quy hoạch Đô thị & Quản lý Đất đai số** | Bản đồ trực quan quy hoạch/phân khu/sử dụng đất; công cụ tra cứu quy hoạch online cho dân, nhà đầu tư, BĐS. |

---

### Việc của team hiện tại ↔ north star

Phần lớn đầu việc 2026.06 phục vụ **nền móng** cho định hướng 1–3 và lĩnh vực **1, 2, 5, 8**:
- Enrichment (maxspeed/biển báo/làn) + cảnh báo lái xe → **lĩnh vực 1** (chỉ dẫn/cảnh báo) + **ĐH 1** (phục vụ cộng đồng).
- POI/Search/Geocoding → **lĩnh vực 2** (local search/commerce).
- Routing/Traffic + hạ tầng MAP_INFS → nền cho **ĐH 2** (hỗ trợ DN/logistics) + **lĩnh vực 6–7**.
- Làm chủ dữ liệu OSM + crowdsource nội bộ → **ĐH 3** (Mobility Data quốc gia).
- HD/ADAS Maps → **lĩnh vực 8** (lộ trình dài hạn, qua đối tác Geely).

Chi tiết trạng thái: xem [orchestrator](../README.md).
