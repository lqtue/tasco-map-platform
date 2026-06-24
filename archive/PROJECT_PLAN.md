  
**ĐỀ XUẤT DỰ ÁN**

**Hệ thống Làm giàu Dữ liệu Giao thông**

**trên Nền tảng Bản đồ Mở OSM**

Phiên bản 1.0  —  Tháng 6 / 2026

**Tasco**

*Tài liệu nội bộ — Không phát hành ra ngoài*

# **Checklist**

- [ ] Bảng tốc độ chuẩn theo luật VN  
- [ ] Tài khoản API Mapillary  
- [ ] Bộ dữ liệu mẫu ngã tư đèn đỏ tại Hà Nội/HCM  
- [ ] Bộ dữ liệu mẫu số làn đường tại VN  
- [ ] Tiêu chuẩn chiều rộng làn đường VN  
- [ ] Nguồn ảnh vệ tinh độ phân giải ≥ 30cm/điểm ảnh

# **Mục lục**

Tóm tắt điều hành

Bối cảnh & Vấn đề

Ba bài toán trọng tâm

Bài toán 1: Giới hạn tốc độ

Bài toán 2: Phát hiện ngã tư có đèn tín hiệu

Bài toán 3: Xác định số làn đường

Nguồn dữ liệu sử dụng

Những gì còn cần chuẩn bị

Lộ trình triển khai

Kết luận

# **Tóm tắt điều hành**

Dữ liệu bản đồ giao thông chính xác là nền tảng của hàng loạt ứng dụng quan trọng: từ ứng dụng dẫn đường, phần mềm tính toán lộ trình cho xe tải, đến các hệ thống hỗ trợ lái xe thông minh. Tuy nhiên, tại Việt Nam, dữ liệu bản đồ mở OSM (OpenStreetMap) — nền tảng bản đồ được hàng nghìn ứng dụng sử dụng — đang thiếu nhiều thông tin quan trọng hoặc ghi nhận sai lệch so với thực tế.

Tasco đề xuất xây dựng một hệ thống tự động kết hợp ba nguồn dữ liệu: ảnh vệ tinh, hình ảnh đường phố từ nền tảng Mapillary, và các văn bản quy phạm pháp luật về giao thông của Việt Nam — để phát hiện và bổ sung các thông tin còn thiếu vào bản đồ OSM một cách có hệ thống và có kiểm soát chất lượng.

| Hệ thống giải quyết 3 bài toán cốt lõi: Xác định giới hạn tốc độ (maxspeed) theo từng loại phương tiện và từng đoạn đường Phát hiện các ngã tư có đèn tín hiệu giao thông còn thiếu trên bản đồ Đếm và ghi nhận chính xác số làn đường cho từng tuyến đường |
| :---- |

Cả ba hạng mục trên đều là dữ liệu nền tảng mà hầu hết các ứng dụng định vị và dẫn đường hiện đại đang cần. Việc bổ sung chúng sẽ nâng cao đáng kể độ chính xác của các sản phẩm sử dụng bản đồ OSM tại thị trường Việt Nam.

# **Bối cảnh & Vấn đề**

## **OSM là gì và tại sao nó quan trọng?**

OpenStreetMap (OSM) là một dự án bản đồ mở toàn cầu, tương tự Wikipedia nhưng dành cho bản đồ — bất kỳ ai cũng có thể đóng góp và sử dụng dữ liệu. Hàng nghìn ứng dụng lớn nhỏ trên thế giới, bao gồm nhiều ứng dụng điều hướng, giao hàng và logistics, đang sử dụng OSM làm nền tảng bản đồ do chi phí thấp và dữ liệu mở.

Tuy nhiên, chất lượng dữ liệu OSM phụ thuộc hoàn toàn vào cộng đồng đóng góp. Tại Việt Nam, mức độ hoàn thiện dữ liệu còn thấp, đặc biệt ở các thông tin chi tiết như giới hạn tốc độ, số làn đường và trạng thái đèn tín hiệu.

## **Vấn đề cụ thể**

| Loại dữ liệu | Hiện trạng tại VN | Tác động thực tế |
| :---- | :---- | :---- |
| **Giới hạn tốc độ** | Phần lớn các tuyến đường thiếu hoàn toàn hoặc ghi sai tốc độ theo loại phương tiện | Ứng dụng dẫn đường không cảnh báo được tốc độ đúng, dữ liệu routing sai |
| **Đèn tín hiệu giao thông** | Nhiều ngã tư có đèn đỏ chưa được đánh dấu trên bản đồ | Phần mềm tính thời gian di chuyển bị sai do không tính thời gian chờ đèn đỏ |
| **Số làn đường** | Đa phần các đường thiếu thông tin số làn, không phân biệt chiều | Không thể tối ưu lộ trình theo làn, ảnh hưởng đến hệ thống dẫn đường nâng cao |

***Lưu ý:** Việc cập nhật thủ công toàn bộ mạng lưới đường bộ Việt Nam là không thực tế. Hệ thống tự động hóa này được thiết kế để giải quyết bài toán ở quy mô lớn.*

# **Ba bài toán trọng tâm**

## **Bài toán 1: Giới hạn tốc độ**

Mục tiêu là tự động xác định và ghi nhận đúng giới hạn tốc độ cho từng đoạn đường, phân biệt theo loại phương tiện (ô tô, xe máy, xe tải nặng).

### **Cách hệ thống hoạt động**

Hệ thống kết hợp hai phương pháp song song rồi so sánh chéo kết quả:

* Phương pháp 1 — Áp dụng luật: Dựa vào Thông tư 38/2021/TT-BGTVT và Nghị định 100/2019, hệ thống tự động gán tốc độ mặc định dựa trên loại đường (quốc lộ, tỉnh lộ, đường đô thị...) và khu vực (nội thành / ngoại thành).

* Phương pháp 2 — Đọc biển báo: Hệ thống quét ảnh đường phố từ nền tảng Mapillary (cộng đồng chia sẻ ảnh đường phố hợp pháp) để phát hiện các biển báo tốc độ thực tế tại từng vị trí.

### **Các loại biển báo được nhận dạng**

| Loại biển | Ký hiệu theo QCVN | Dữ liệu khai thác được |
| :---- | ----- | :---- |
| Biển tốc độ thông thường | P.127 | Tốc độ tối đa cho tất cả phương tiện trên đoạn đường đó |
| Biển khu đông dân cư | R.420 / R.421 | Xác định ranh giới khu đô thị — làm cơ sở áp dụng bảng tốc độ đúng theo luật |
| Biển tốc độ theo làn / theo loại xe | P.127a, P.127b, P.127c | Tốc độ riêng biệt cho từng nhóm phương tiện hoặc từng làn đường |

### **Cơ chế kiểm soát chất lượng**

Khi kết quả từ hai phương pháp nhất quán với nhau, dữ liệu được tự động xác nhận và cập nhật lên bản đồ. Khi có mâu thuẫn (ví dụ: biển báo ghi 40km/h nhưng luật quy định 60km/h), hệ thống sẽ đưa trường hợp đó vào danh sách chờ để người kiểm duyệt xem xét thủ công trước khi quyết định.

***Lưu ý:** Google Street View không được sử dụng vì điều khoản dịch vụ của Google cấm khai thác dữ liệu để tạo bản đồ. Mapillary được lựa chọn vì là nền tảng mở, được phép sử dụng cho mục đích này.*

## **Bài toán 2: Phát hiện ngã tư có đèn tín hiệu**

Mục tiêu là xác định các ngã tư có đèn tín hiệu giao thông đang thiếu trên bản đồ OSM, qua đó giúp phần mềm dẫn đường tính chính xác thời gian chờ đèn đỏ vào tổng thời gian di chuyển.

### **Tại sao điều này quan trọng?**

| Ví dụ thực tế: Một lộ trình từ điểm A đến B đi qua 8 ngã tư đèn đỏ, mỗi ngã tư chờ trung bình 60 giây. Nếu bản đồ không ghi nhận các ngã tư này, phần mềm sẽ ước tính thời gian di chuyển thiếu khoảng 8 phút — sai lệch lớn với các ứng dụng giao hàng hoặc logistics yêu cầu độ chính xác cao. |
| :---- |

### **Cách hệ thống phát hiện ngã tư có đèn**

Hệ thống không duyệt toàn bộ bản đồ mà hoạt động theo 3 bước có chọn lọc:

1. **Bước 1 — Lọc ứng cử viên:**

   * Chỉ xem xét các giao lộ có từ 3 đường trở lên, nằm trên trục đường cấp cao (quốc lộ, tỉnh lộ, đường chính đô thị) và ở khu vực đô thị.

2. **Bước 2 — Xác nhận bằng ảnh:**

   * Nếu có ảnh đường phố Mapillary gần đó: phân tích ảnh để nhận diện cột đèn tín hiệu, vạch kẻ đường, vạch dành cho người đi bộ.

   * Nếu không có ảnh đường phố: sử dụng ảnh vệ tinh để phát hiện cấu trúc ngã tư từ trên cao.

3. **Bước 3 — Phân loại đúng loại đèn:**

   * Phân biệt ngã tư có đèn điều phối thực sự (đèn xanh/đỏ theo chu kỳ) với ngã tư chỉ có đèn chớp vàng cảnh báo — hai loại này có tác động khác nhau lên việc tính thời gian di chuyển.

## **Bài toán 3: Xác định số làn đường**

Mục tiêu là xác định chính xác số làn xe trên từng đoạn đường, bao gồm phân biệt số làn theo từng chiều — thông tin hiện đang thiếu ở phần lớn mạng lưới đường bộ Việt Nam trên OSM.

### **Phương pháp tiếp cận: kết hợp trí tuệ nhân tạo và quy tắc**

Hệ thống sử dụng mô hình nhận diện hình ảnh (AI) được huấn luyện để phân tích ảnh vệ tinh, phát hiện vạch kẻ đường và mũi tên chỉ hướng. Tuy nhiên, dựa trên kinh nghiệm từ các nghiên cứu quốc tế, phần kết luận cuối cùng về số làn được giao cho bộ quy tắc dựa trên tiêu chuẩn kỹ thuật đường bộ Việt Nam (TCVN 4054, QCVN 41).

| Tại sao không dùng AI hoàn toàn? Theo nghiên cứu quốc tế (Hugo Nilsson, 2024), AI đạt độ chính xác rất cao khi phát hiện vạch kẻ và mũi tên trên ảnh, nhưng lại kém hơn hẳn so với quy tắc hình học trong việc suy luận kết nối giữa các làn tại ngã tư phức tạp. Chiến lược phù hợp là: AI làm nhiệm vụ "nhìn" (phát hiện đối tượng), quy tắc làm nhiệm vụ "suy nghĩ" (kết luận cấu trúc làn). |
| :---- |

### **Đặc thù Việt Nam cần xử lý**

* Vạch kẻ đường VN dùng màu vàng (khác với trắng ở châu Âu) — mô hình AI cần được huấn luyện lại trên dữ liệu Việt Nam.

* Nhiều tuyến đường đô thị không có vạch phân làn rõ ràng — hệ thống sẽ không gán số làn theo chiều rộng đường nếu không có vạch để tránh sai số.

* Làn hỗn hợp (một làn cho phép cả đi thẳng lẫn rẽ) rất phổ biến tại VN — cần được ưu tiên thu thập mẫu dữ liệu huấn luyện.

# **Nguồn dữ liệu sử dụng**

Hệ thống được thiết kế để khai thác tối đa các nguồn dữ liệu có sẵn hoặc có thể tiếp cận, nhằm giảm thiểu chi phí thu thập mới.

| Nguồn dữ liệu | Nội dung cung cấp | Chi phí tiếp cận | Sử dụng cho bài toán |
| :---- | :---- | :---- | :---- |
| **OSM (OpenStreetMap)** | Dữ liệu đường bộ hiện có: loại đường, tọa độ, các thông tin đã gắn tag | Miễn phí, mở hoàn toàn | Cả 3 bài toán (nền tảng) |
| **Mapillary** | Ảnh đường phố do cộng đồng đóng góp, kèm nhãn biển báo giao thông tự động | Miễn phí (cần tạo tài khoản API) | Bài toán 1 (biển tốc độ), Bài toán 2 (đèn tín hiệu) |
| **Ảnh vệ tinh (Google Earth Engine)** | Ảnh chụp từ trên cao độ phân giải 30cm–1m, phủ toàn lãnh thổ | Có bản miễn phí, cần phê duyệt tài khoản | Bài toán 2 & 3 (phát hiện ngã tư, đếm làn) |
| **Ảnh vệ tinh độ phân giải cao (Maxar)** | Ảnh chi tiết hơn (30cm/điểm ảnh) cho các ngã tư phức tạp | Có phí — chỉ dùng có chọn lọc tại các điểm cần thiết | Bài toán 2 & 3 (xác nhận chi tiết) |
| **Văn bản pháp luật VN** | Thông tư 38/2021, Nghị định 100/2019, QCVN 41:2019, TCVN 4054, TCVN 5729 | Miễn phí, công khai | Bài toán 1 (bảng tốc độ), Bài toán 3 (chuẩn chiều rộng làn) |

***Lưu ý:** Đối với ảnh vệ tinh, chiến lược tối ưu chi phí là: dùng Google Earth Engine (miễn phí) để quét diện rộng và xác định các vị trí nghi ngờ, sau đó chỉ mua ảnh Maxar độ phân giải cao cho đúng các vị trí đó.*

# **Những gì còn cần chuẩn bị**

Dưới đây là danh sách các hạng mục cần được hoàn thiện trước khi từng phần của hệ thống có thể vận hành. Các hạng mục được phân loại theo mức độ ưu tiên.

## **Nhóm Bắt buộc — Hệ thống không vận hành được nếu thiếu**

| Hạng mục cần có | Mức độ ưu tiên | Mục đích |
| :---- | :---: | :---- |
| **Bảng tốc độ chuẩn theo luật VN** | **Bắt buộc** | Parse từ Thông tư 38/2021 và Nghị định 100/2019 thành bảng tra cứu máy đọc được |
| **Tài khoản API Mapillary** | **Bắt buộc** | Cần tạo ứng dụng tại mapillary.com để truy vấn biển báo; cần kiểm tra phạm vi phủ sóng tại VN |
| **Bộ dữ liệu mẫu ngã tư đèn đỏ tại Hà Nội/HCM** | **Bắt buộc** | Tập hợp danh sách ngã tư đã xác nhận có đèn tín hiệu để kiểm tra độ chính xác của mô hình |
| **Bộ dữ liệu mẫu số làn đường tại VN** | **Bắt buộc** | Ảnh vệ tinh đã gán nhãn số làn — dùng để huấn luyện và kiểm tra mô hình nhận diện |
| **Tiêu chuẩn chiều rộng làn đường VN** | **Bắt buộc** | TCVN 4054:2005, TCVN 5729:2012, QCVN 41:2019 — làm cơ sở cho bộ quy tắc xác nhận số làn |
| **Nguồn ảnh vệ tinh độ phân giải ≥ 30cm/điểm ảnh** | **Bắt buộc** | Google Earth Engine hoặc Maxar; nghiên cứu quốc tế cho thấy dưới ngưỡng này độ chính xác giảm mạnh |

## **Nhóm Quan trọng — Ảnh hưởng đáng kể đến chất lượng kết quả**

| Hạng mục cần có | Mức độ ưu tiên | Mục đích |
| :---- | :---: | :---- |
| Công cụ gán biển báo vào đoạn đường tương ứng | **Quan trọng** | Xử lý trường hợp biển báo đặt trước 50–100m, hoặc nằm gần ngã tư nhiều đường |
| Kiểm tra mẫu nhận diện biển báo VN từ Mapillary | **Quan trọng** | Mapillary chủ yếu học từ biển báo châu Âu — cần đánh giá tỷ lệ nhầm trên biển VN |
| Huấn luyện lại mô hình nhận diện vạch kẻ VN | **Quan trọng** | Vạch kẻ đường VN dùng màu vàng, khác chuẩn quốc tế — mô hình cần được điều chỉnh |
| Bộ quy tắc xử lý mâu thuẫn dữ liệu | **Quan trọng** | Logic phân xử khi biển báo Mapillary mâu thuẫn với quy định pháp luật mặc định |
| Ảnh đường phố cho đường hẹp nội đô | **Quan trọng** | Ảnh vệ tinh khó phân biệt làn trên đường nhỏ hơn 3.5m — cần ảnh đường phố để bù trợ |

## **Nhóm Nên có — Hỗ trợ vận hành lâu dài**

| Hạng mục cần có | Mức độ ưu tiên | Mục đích |
| :---- | :---: | :---- |
| Bộ lọc biển báo tạm thời (công trình) | **Nên có** | Loại bỏ biển tốc độ 40/30 km/h của công trình thi công khỏi dữ liệu chính thức |
| Bảng tra cứu quy ước tag OSM tại VN | **Nên có** | Đảm bảo dữ liệu được gắn đúng theo tiêu chuẩn cộng đồng OSM Việt Nam |
| Bảng điều khiển kiểm duyệt thủ công | **Nên có** | Giao diện để reviewer xem xét và xử lý các trường hợp mâu thuẫn chưa giải quyết tự động được |
| Báo cáo chất lượng định kỳ theo khu vực | **Nên có** | Theo dõi tỷ lệ chính xác và phạm vi phủ sóng theo từng tỉnh/thành phố |
| Tự động hóa chạy lại định kỳ | **Nên có** | Hệ thống tự cập nhật khi có ảnh vệ tinh mới hoặc khi cộng đồng bổ sung ảnh Mapillary |

# **Lộ trình triển khai**

Dự án được chia thành 4 giai đoạn, ước tính tổng thời gian từ 4 đến 5 tháng để hoàn thành pilot và bắt đầu triển khai diện rộng.

| Giai đoạn | Thời gian | Nội dung công việc | Kết quả bàn giao |
| ----- | :---: | :---- | :---- |
| **Phase 1** Nền tảng | Tuần 1 – 4 | Thu thập và số hóa văn bản luật tốc độ VN Xây dựng bộ quy tắc tốc độ mặc định theo loại đường Thiết lập tài khoản Mapillary API Thu thập tiêu chuẩn kỹ thuật TCVN/QCVN | Bộ quy tắc tốc độ \+ kết nối Mapillary API hoạt động |
| **Phase 2** Dữ liệu | Tuần 5 – 9 | Xây dựng bộ dữ liệu mẫu ngã tư đèn đỏ (Hà Nội / HCM) Xây dựng bộ dữ liệu mẫu số làn đường VN Xây dựng công cụ gán biển báo vào đoạn đường OSM Thiết kế mẫu truy vấn tìm ngã tư thiếu đèn | Hai bộ dữ liệu mẫu \+ công cụ xử lý biển báo |
| **Phase 3** Mô hình | Tuần 10 – 16 | Huấn luyện mô hình nhận diện làn đường trên ảnh VN Huấn luyện mô hình phát hiện đèn tín hiệu Xây dựng bộ quy tắc xử lý mâu thuẫn dữ liệu | Hai mô hình nhận diện đã điều chỉnh cho VN \+ bộ quy tắc |
| **Phase 4** Triển khai | Tuần 17 – 22 | Kiểm thử toàn hệ thống tại khu vực pilot (1 quận/huyện) Vận hành bảng điều khiển kiểm duyệt thủ công Cập nhật dữ liệu lên OSM sau khi kiểm duyệt Đánh giá kết quả và lên kế hoạch mở rộng toàn quốc | Dữ liệu OSM được cập nhật tại khu vực pilot \+ báo cáo chất lượng |

# **Kết luận**

Hệ thống đề xuất tiếp cận bài toán làm giàu dữ liệu bản đồ giao thông theo hướng kết hợp thực dụng giữa dữ liệu nguồn mở sẵn có (OSM, Mapillary, ảnh vệ tinh miễn phí), quy định pháp lý Việt Nam, và các nghiên cứu học thuật đã được kiểm chứng — thay vì xây dựng từ đầu.

Chiến lược quan trọng nhất là không hoàn toàn phụ thuộc vào trí tuệ nhân tạo: AI được dùng ở những việc nó làm tốt (nhận diện hình ảnh), còn các quyết định cần sự chắc chắn cao (kết luận về tốc độ hay cấu trúc làn) được giao cho bộ quy tắc dựa trên luật và tiêu chuẩn — kết hợp với kiểm duyệt thủ công ở những trường hợp mâu thuẫn.

| Các bước ưu tiên tiếp theo: Thu thập và số hóa Thông tư 38/2021 và TCVN liên quan Đăng ký tài khoản Mapillary API và đánh giá phạm vi phủ sóng tại Hà Nội / HCM Bắt đầu gán nhãn thủ công bộ dữ liệu mẫu ngã tư và số làn tại 1 quận thí điểm Xác nhận nguồn ảnh vệ tinh (Google Earth Engine) và tạo tài khoản |
| :---- |

Ba bước đầu tiên trên có thể thực hiện song song và là điều kiện tiên quyết để toàn bộ dự án có thể khởi động. Khuyến nghị hoàn thành trong vòng 4 tuần đầu để không làm chậm các giai đoạn tiếp theo.

# **Tài liệu tham khảo**

Các nghiên cứu dưới đây làm cơ sở học thuật cho thiết kế hệ thống, được xác minh qua chỉ mục trích dẫn khoa học (scite). Liên kết theo định dạng `https://doi.org/{doi}`. Phiên bản chú giải đầy đủ (kèm trích dẫn số liệu) xem tại `research/README.md`.

***Lưu ý về nguồn "Hugo Nilsson, 2024":** Nguồn này không có trong kho dữ liệu học thuật bình duyệt (nhiều khả năng là luận văn chưa được lập chỉ mục). Luận điểm cốt lõi "AI nhận diện — quy tắc kết luận" được thay thế bằng nguồn bình duyệt **He et al. (2020) — RoadTagger** (xem Bài toán 3).*

## **Cơ sở phương pháp luận chung (OSM, viễn thám, chất lượng dữ liệu)**

1. Vargas-Munoz, J. E., Srivastava, S., & Tuia, D. (2021). OpenStreetMap: Challenges and opportunities in machine learning and remote sensing. *IEEE Geoscience and Remote Sensing Magazine, 9*(1). https://doi.org/10.1109/mgrs.2020.2994107
2. Mo, S., Shi, Y., & Yuan, Q. (2024). A survey of deep learning road extraction algorithms using high-resolution remote sensing images. *Sensors, 24*(5), 1708. https://doi.org/10.3390/s24051708
3. Usmani, M., Bovolo, F., & Napolitano, M. (2023). Remote sensing and deep learning to understand noisy OpenStreetMap. *Remote Sensing, 15*(18), 4639. https://doi.org/10.3390/rs15184639
4. Xie, X., Zhou, Y., & Xu, Y. (2019). OpenStreetMap data quality assessment via deep learning and remote sensing imagery. *IEEE Access, 7.* https://doi.org/10.1109/access.2019.2957825
5. Almendros-Jiménez, J. M., & Becerra-Terón, A. (2018). Analyzing the tagging quality of the Spanish OpenStreetMap. *ISPRS International Journal of Geo-Information, 7*(8), 323. https://doi.org/10.3390/ijgi7080323

## **Bài toán 1 — Giới hạn tốc độ**

6. Guth, J., Wursthorn, S., & Keller, S. (2020). Multi-parameter estimation of average speed in road networks using fuzzy control. *ISPRS International Journal of Geo-Information, 9*(1), 55. https://doi.org/10.3390/ijgi9010055
7. Ajmar, A., Arco, E., & Boccardo, P. (2019). Updating a road network dataset exploiting the results of semantic segmentation techniques applied to street-level imagery. *Int. Arch. Photogramm. Remote Sens. Spatial Inf. Sci., XLII-2/W13,* 1511–1517. https://doi.org/10.5194/isprs-archives-xlii-2-w13-1511-2019
8. Romijnders, R., Meletis, P., & Dubbelman, G. (2019). A domain-agnostic normalization layer for unsupervised adversarial domain adaptation. *IEEE WACV.* https://doi.org/10.1109/wacv.2019.00203
9. Tusher, M. M. R., Al Farid, F., & Kafi, H. M. (2024). BanTrafficNet: Bangladeshi traffic sign recognition using a lightweight deep learning approach. *Research Square* (preprint). https://doi.org/10.21203/rs.3.rs-4216970/v1
10. Ruiz, I., & Serrat, J. (2022). Hierarchical novelty detection for traffic sign recognition. *Sensors, 22*(12), 4389. https://doi.org/10.3390/s22124389
11. Jaghouar, S., Gustafsson, H., & Mehlig, B. (2021). Improving traffic sign recognition by active search. *arXiv.* https://doi.org/10.48550/arxiv.2111.14426

## **Bài toán 2 — Phát hiện ngã tư có đèn tín hiệu**

12. Zhang, C., Fan, H., & Li, W. (2021). Automated detecting and placing road objects from street-level images. *Computational Urban Science, 1,* 18. https://doi.org/10.1007/s43762-021-00019-6
13. Krylov, V. A., & Dahyot, R. (2019). Object geolocation from crowdsourced street level imagery. *Springer.* https://doi.org/10.1007/978-3-030-13453-2_7
14. Qiu, S., Psyllidis, A., & Bozzon, A. (2019). Crowd-mapping urban objects from street-level imagery. *ACM WWW.* https://doi.org/10.1145/3308558.3313651
15. Mentasti, S., Simsek, Y. C., & Matteucci, M. (2023). Traffic lights detection and tracking for HD map creation. *Frontiers in Robotics and AI, 10,* 1065394. https://doi.org/10.3389/frobt.2023.1065394
16. Wijnands, J. S., Zhao, H., & Nice, K. A. (2020). Identifying safe intersection design through unsupervised feature extraction from satellite imagery. *Computer-Aided Civil and Infrastructure Engineering, 35*(7). https://doi.org/10.1111/mice.12623
17. Ng, V., & Hofmann, D. (2018). Scalable feature extraction with aerial and satellite imagery. *SciPy.* https://doi.org/10.25080/majora-4af1f417-015

## **Bài toán 3 — Xác định số làn đường**

18. He, S., Bastani, F., & Jagwani, S. (2020). RoadTagger: Robust road attribute inference with graph neural networks. *Proceedings of the AAAI Conference on Artificial Intelligence, 34*(07), 10965–10972. https://doi.org/10.1609/aaai.v34i07.6730  *(nguồn cốt lõi: độ chính xác đếm làn tăng từ 71.8% lên 77.2% khi bổ sung suy luận theo đồ thị)*
19. Zang, A., Xu, R., & Li, Z. (2017). Lane boundary extraction from satellite imagery. *ACM SIGSPATIAL.* https://doi.org/10.1145/3149092.3149093
20. Yan, J., Ji, S., & Yao, W. (2022). A combination of convolutional and graph neural networks for regularized road surface extraction. *IEEE Transactions on Geoscience and Remote Sensing, 60,* 1–13. https://doi.org/10.1109/tgrs.2022.3151688
21. Kasmi, A., Denis, D., & Aufrère, R. (2018). Map matching and lanes number estimation with OpenStreetMap. *IEEE ITSC,* 2659–2664. https://doi.org/10.1109/itsc.2018.8569840
22. Van Etten, A. (2019). City-scale road extraction from satellite imagery v2: Road speeds and travel times (CRESIv2). *arXiv.* https://doi.org/10.48550/arxiv.1908.09715

*Tài liệu soạn thảo bởi nhóm kỹ thuật Tasco  —  Tháng 6/2026*