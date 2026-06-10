# Research To-Dos từ buổi họp 08/06/2026
> *Cập nhật 2026-06-09 · [🧭 Orchestrator](../README.md) · [North Star](../vision/tasco-mobility-platform.md)*

Tổng hợp các hướng **nghiên cứu / tra nguồn** mà Anh (CTO) yêu cầu trong buổi họp, kèm **brief review đã verify bằng scite MCP** (chỉ trích dẫn paper thực sự truy xuất được; link DOI ở cuối). Đi kèm biên bản [2026-06-08-team-sync.md](./2026-06-08-team-sync.md).

> **Nguyên tắc Anh chốt:** mọi quyết định model/metric phải **refer được về nguồn gốc** — paper / thesis / patent (RAP, Uber, Google) / original work — để chứng minh và để dùng ngôn ngữ chung. Scite MCP (gói 250 request) dùng để check nguồn, ít hallucinate.

---

## Danh sách hướng nghiên cứu (theo người)

| # | Hướng nghiên cứu | Anh yêu cầu để làm gì | Chủ trì |
|---|---|---|---|
| R-1 | **RoadTagger (MIT)** — đọc original work | Keystone cho kiến trúc "AI detect, graph reason" của speed limit / lane | Tuệ |
| R-2 | **Speed limit inference từ OSM / road graph** | Auto-điền maxspeed cho đoạn thiếu, làm decision-tree | Tuệ + Quân |
| R-3 | **Đo traffic/vehicle từ ảnh vệ tinh ("dùng S đo")** | Paper Anh thấy về dùng ảnh đo được lưu lượng/tốc độ — bàn riêng với anh Phụng | Tuệ |
| R-4 | **Metric UX map mobile (lab Thụy Sĩ / Tokyo)** | Benchmark sản phẩm; timeline tiến hóa số liệu Google Maps | Thiện |
| R-5 | **Map feedback / VGI crowdsourcing** (bài Google ~2010) | Đo thời gian user feedback thành công; chiến dịch crowdsource ảnh | Thiện + Tuệ |
| R-6 | **Retention / engagement benchmark** (Waze D7 = 22%) | Đối chiếu số sản phẩm với industry | Thiện |
| R-7 | **Map matching GPS low-sampling** | Split way theo biển báo; gộp GPS tài xế → live traffic (Bahala) | Huy + Tuệ |

---

## Brief review (scite-verified)

### R-1 — RoadTagger: keystone cho "AI detect, graph reason"
Xác nhận đúng nguồn CLAUDE.md yêu cầu cite. RoadTagger kết hợp **CNN (perception) + Graph Neural Network (reasoning)** để suy ra thuộc tính đường (số làn, loại đường) từ ảnh vệ tinh + đồ thị đường — vượt giới hạn "receptive field" của image classifier thuần bằng cách lan truyền thông tin trên graph (He et al., 2020). Đánh giá trên 688 km² / 20 thành phố Mỹ. Đây chính là chỗ dựa học thuật cho nguyên tắc kiến trúc của dự án (CNN detect, graph/rule reason).
- **Hệ sinh thái cùng nhóm MIT (Bastani/He)** đáng đọc kèm: RoadTracer trích đồ thị đường từ ảnh (Bastani et al., 2018a); **MAiD — machine-assisted map editing** tích hợp suy luận tự động vào workflow biên tập OSM (iD editor), user thêm được tới **3.5× đường** trong cùng thời gian (Bastani et al., 2018b) — rất sát mô hình "tool internal cho Map Operations" Anh muốn.
- Mở rộng CNN+GNN cho trích bề mặt đường: Yan et al. (2022) — và chính paper này xác nhận "Jepsen et al. thiết kế GCN cho **speed limit**", nối sang R-2.

### R-2 — Speed limit inference: literature ủng hộ cách làm, và xác nhận con số "thiếu maxspeed"
Nhánh này **củng cố trực tiếp baseline của Tuệ** (VN tertiary+ chỉ 12.9% có maxspeed):
- **Con số thiếu maxspeed là vấn đề toàn cầu, không riêng VN:** "92.2% tổng số km đường toàn thế giới trong OSM 2019 thiếu thông tin maxspeed" (Keller et al., 2020). Keller dùng ML ước lượng **tốc độ trung bình** đường nông thôn chỉ từ thuộc tính OSM, R²≈80%, không cần domain knowledge — mô hình tham chiếu tốt cho lớp "auto-điền theo dữ liệu".
- **GCN cho road network là hướng SOTA cho speed-limit classification:** node2vec embedding cho phân loại speed limit (Jepsen et al., 2018; lưu ý họ cũng báo OSM Đan Mạch chỉ 13% đoạn có speed limit); và **Relational Fusion Network** — GCN thiết kế riêng cho đường, vượt GCN tiêu chuẩn **21–24% ở speed-limit classification** và 32–40% ở driving-speed estimation (Jepsen et al., 2019, 2022).
- **Từ ảnh vệ tinh trực tiếp ra speed + travel time:** CRESIv2 trích đồ thị đường kèm speed limit từ ảnh, nhãn SpaceNet tốt hơn nhãn OSM ≥60% (Van Etten, 2019) — đáng tham chiếu cho phần "có ảnh thì điền".
- **Hàm ý cho decision-tree của Tuệ/Quân:** literature đồng thuận đường thiếu attribute → khai thác **cấu trúc graph + luật** để bù; đúng tinh thần "AI detect, rules/graph reason". Quân's bảng luật = lớp prior; ML/GNN = lớp dữ liệu; scoring trọng số khi lệch.

### R-3 — Đo từ ảnh vệ tinh: cẩn trọng về kỳ vọng
Quan trọng để set kỳ vọng với anh Phụng: literature mạnh ở **đếm xe / ước lượng lưu lượng**, **yếu/hiếm ở đo tốc độ tức thời** từ một ảnh quang học.
- Đếm/đo lưu lượng xe nặng từ ảnh Google Earth cho **road-safety toàn quốc** (Goel et al., 2020, Ấn Độ) — tương quan Pearson 0.84 với đếm thực địa; mô hình rất hợp cảnh VN (quốc lộ + dân cư ven đường).
- Vehicle detection từ ảnh vệ tinh độ phân giải cao: SatDetX-YOLO (Zhao et al., 2024), dataset VME/CDSI Trung Đông (Al Emadi et al., 2025) — phục vụ detect, **không** ra tốc độ.
- **Một nguồn "Thụy Sĩ" có thật trong corpus:** ước lượng **traffic noise** từ Sentinel-2 bằng U-Net, train trên dữ liệu Thụy Sĩ (Eicher, Mommert & Borth, 2022, ĐH St. Gallen) — nếu paper anh Phụng nhắc dùng "S" = **Sentinel**, nhiều khả năng thuộc dòng này (suy ra biến giao thông gián tiếp từ ảnh phổ), không phải đo tốc độ trực tiếp. **Cần Anh/anh Phụng xác nhận đúng paper trước khi đầu tư.**

### R-4 — Metric UX map mobile: chưa tìm thấy đúng "bài Tokyo/ETH Google-sponsored", nhưng có khung metric dùng được
- **Chưa verify được** paper cụ thể từ lab Tokyo hoặc ETH Zürich do Google Maps tài trợ mà Anh nhắc — các query chưa trả về đúng bài đó. Cần Anh chỉ tên/tác giả cụ thể để tra đích danh (scite hỗ trợ filter `affiliation`).
- **Khung metric có sẵn, đã verify:** một usability study so sánh app bản đồ định nghĩa rõ **completion ratio**, **accuracy ratio (số click thực / kỳ vọng)**, và **memorability = thời gian thao tác thành công sau khi ngừng dùng 5 ngày** + PSSUQ 19 câu (Thanachan & Jiamsanguanwong, 2016) — chính cái "thời gian user làm thành công" Anh mô tả. Bartling et al. (2021, ĐH Salzburg) đo usability theo **ngữ cảnh sử dụng** + base-map style bằng archetypal analysis — nối thẳng vào ý Anh "map type/base map config theo ngữ cảnh". Li et al. (2024) về nhu cầu thông tin theo ngữ cảnh ngoài navigation.
- **Việc cho Thiện:** dựng file metric (5 màn hình) bám các định nghĩa academic này thay vì tự chế; xin Anh tên bài Google/Tokyo để tra đích danh.

### R-5 — Map feedback & VGI crowdsourcing: nền tảng cho chiến dịch ảnh + màn hình community
- **Bài Google ~2010 chưa tra được đích danh** (cần keyword/tác giả từ Anh). Nhưng VGI literature cung cấp khung:
- **Quy luật 90-9-1**: ~1% contributor tạo phần lớn dữ liệu (Forati & Ghose, 2020) — hệ quả: chiến dịch crowdsource ảnh nội bộ phải thiết kế incentive (KPI/Loyalty như Anh nói) để kéo nhóm 1% đó.
- **Taxonomy 11 phương pháp đánh giá chất lượng CGI khi không có ground-truth** (Degrossi et al., 2018), gồm cross-validation giữa nhiều volunteer + feedback chuyên gia — dùng cho lớp QA của Map Operations. Foody et al. (2015): có thể xếp hạng chất lượng volunteer chỉ từ dữ liệu họ đóng góp.
- **VGI làm dữ liệu "tươi" hơn trong cảm nhận user** (Parker et al., 2014) — luận cứ cho màn hình thứ 5 (community report). App VGI báo **điểm tai nạn giao thông** đã có tiền lệ (Sevinç et al., 2020) — đúng tính năng report Thiện đang phân vân build.

### R-6 — Retention/engagement: số 22% cần nguồn industry, nhưng có bằng chứng học thuật cho hướng crowdsource
- **Cảnh báo nguồn:** "Waze D7 retention global = 22%" là số **industry analytics** (data.ai / Sensor Tower…), **scite không validate** được vì không phải literature peer-reviewed. Thiện nên trích nguồn industry trực tiếp cho con số này, đừng gắn vào academic citation.
- **Định nghĩa chuẩn DAU/MAU/churn** có trong literature (Edney et al., 2019; Lin et al., 2020) — dùng để chuẩn hóa cách đo.
- **Bằng chứng mạnh ủng hộ chiến lược crowdsource + community screen:** thí nghiệm randomized field (Management Science) cho thấy tính năng **cho user submit nội dung giảm hazard rời app ~14%**, truy cập nội dung crowdsource giảm ~13% (Gu, Bapna & Chan, 2022). Liu et al. (2019, Snapchat): mô hình in-app action graph dự báo engagement. Lin et al. (2020): **passive GPS data giữ chân tốt hơn active** — hàm ý cho telemetry tài xế.

### R-7 — Map matching low-sampling: nền cho split-way & live traffic
Nối hai task kỹ thuật trong họp: (a) map-match biển báo vuông góc rồi **split way** (Tuệ), (b) gộp GPS tài xế → xanh-đỏ-tím-vàng trên Way ID (Huy/Bahala). Vấn đề lõi: GPS tần số thấp + đường đô thị phức tạp gây mismatch.
- Collaborative MM gom trajectory tương tự rồi resample để bù tần số thấp (Bian et al., 2020); MM low-frequency theo **phân đoạn hướng đi xe** + HMM (Yu et al., 2022); MM tại **giao lộ** cho dữ liệu tần số cao (Liu et al., 2020). Bộ này là điểm khởi đầu chuẩn cho pipeline matching của mình, và liên quan trực tiếp tới vấn đề "1 way ↔ 2 làn thực tế" + Way-ID lệch giữa display map và traffic map (vụ Trần Văn Lai).

---

## Papers anh Phụng gửi (screen capture / file) — ưu tiên line của Tuệ

> Anh Phụng hay gửi paper dưới dạng **screen capture** hoặc PDF để "tái hiện cho hiệu quả cao nhất". Mục này gom các bài đó. Chỉ liệt kê bài đã **xác minh được** (DOI thật / có file gốc trong tay). **Còn screen capture nào khác Tuệ gửi vào, sẽ bổ sung tiếp.**

### ⭐ TRỰC TIẾP line của Tuệ — Lane-level mapping từ crowdsource + ảnh vệ tinh (Liu et al., 2026)
**City-Scale Lane-Level Mapping From Crowdsourced Trajectories and Satellite Imagery** — IEEE Robotics and Automation Letters 11(4):4793–4800, nhóm **AMap (Alibaba)** (đã verify scite, DOI 10.1109/lra.2026.3664665; closed access ~$45.95, mới đọc abstract).

Đây là **bản công nghiệp 2026 của đúng cách Tuệ đang làm**: framework tự động fuse **trajectory crowdsource + ảnh vệ tinh** → bản đồ **lane-level vector hoá** quy mô thành phố. Pipeline (theo abstract): mine **hàng tỷ trajectory** trích cấu trúc hình học + topology đường → **multimodal fusion** (trajectory ⊕ satellite) → **spatiotemporal prior-fusion decoding** cho vectorized map-element perception → bản đồ lane-level nhất quán toàn cục. Đạt **SOTA mAP** trên dataset tự thu + **Argoverse 2**; đã chạy trên **>1 triệu km** đường.

**Vì sao đây là bài quan trọng nhất với Tuệ:**
- **Chứng minh khả thi ở quy mô quốc gia** cho đúng 2 thứ TASCO có sẵn: **GPS tài xế (VETC ~2M txn/ngày)** + **ảnh vệ tinh mua** (buy-envelope ~20,350 km² của Tuệ) → nối thẳng chiến dịch crowdsource (T-4) + lane inference (R-1).
- **Lane-level > HD/SD** về trade-off "chi tiết × phủ × độ tươi" — đúng luận điểm "map tươi, lane-level alert" (selling point của dashboard, đúng mandate "just-in-time alerts" trong JD).
- **AMap = peer công nghiệp trực tiếp** → ngôn ngữ chung + benchmark khi present (Argoverse 2 là chuẩn công khai để mình so).
- Bổ sung cho [[R-1]] RoadTagger (CNN+GNN, attribute từ ảnh tĩnh): RoadTagger thiếu lớp **trajectory**; bài này cho thấy thêm GPS làm tăng độ chính xác lane/topology — gợi ý kiến trúc cho Tuệ là **CNN(ảnh) + trajectory fusion + graph/luật**.
- **Cần:** mua/library để đọc Method (multimodal fusion + spatiotemporal decoding) trước khi tái hiện; xác định dataset format để map sang dữ liệu VN.

### Bài nền tảng / hạ tầng (tìm thấy file local — *cần Tuệ xác nhận có phải Phụng gửi không*)
- **Ratnamaheson, N. (2025)** — *A framework for on-demand creation of vector tiles for OpenStreetMap data* (Masterarbeit, Univ. Stuttgart, Prof. Funke). On-demand vector tile từ OSM → liên quan **serving/tile + map ops playground** (line Huy/Vũ hơn là Tuệ), nhưng hữu ích cho phần render lớp traffic-sign/lane lên map.
- **Gonçalves, A. P. (2023)** — *Map Services Management* (MSc, Porto). Quản lý dịch vụ bản đồ / tile serving → cũng nghiêng **hạ tầng** (Huy/Vũ).

---

## Việc cần Anh / anh Phụng xác nhận để tra tiếp
1. **Tên/tác giả bài "dùng S đo"** (R-3) — Sentinel? SAR? đo tốc độ hay lưu lượng? → tra đích danh.
2. **Bài Google ~2010 về map feedback** (R-5) và **bài lab Tokyo / ETH** (R-4) — cho keyword/tác giả để filter `affiliation`.
3. **Patent RAP/Uber/Google** Anh nhắc — scite có `search_patents`; cần tên công ty/chủ đề cụ thể để chạy.

---

## References (APA)

- Al Emadi, N., Weber, I., & Yang, Y. (2025). VME: A satellite imagery dataset and benchmark for detecting vehicles in the Middle East and beyond. *Scientific Data, 12*(1). https://doi.org/10.1038/s41597-025-04567-y
- Bartling, M., Havas, C., & Wegenkittl, S. (2021). Modeling patterns in map use contexts and mobile map design usability. *ISPRS International Journal of Geo-Information, 10*(8), 527. https://doi.org/10.3390/ijgi10080527
- Bastani, F., He, S., Abbar, S., et al. (2018a). RoadTracer: Automatic extraction of road networks from aerial images. *CVPR 2018*, 4720–4728. https://doi.org/10.1109/cvpr.2018.00496
- Bastani, F., He, S., Abbar, S., et al. (2018b). Machine-assisted map editing. *ACM SIGSPATIAL 2018*, 23–32. https://doi.org/10.1145/3274895.3274927
- Bian, W., Cui, G., & Wang, X. (2020). A trajectory collaboration based map matching approach for low-sampling-rate GPS trajectories. *Sensors, 20*(7), 2057. https://doi.org/10.3390/s20072057
- Degrossi, L. C., de Albuquerque, J. P., dos Santos Rocha, R., et al. (2018). A taxonomy of quality assessment methods for volunteered and crowdsourced geographic information. *Transactions in GIS, 22*(2), 542–560. https://doi.org/10.1111/tgis.12329
- Edney, S., Ryan, J., Olds, T., et al. (2019). User engagement and attrition in an app-based physical activity intervention. *Journal of Medical Internet Research, 21*(11), e14645. https://doi.org/10.2196/14645
- Eicher, L., Mommert, M., & Borth, D. (2022). Traffic noise estimation from satellite imagery with deep learning. *IGARSS 2022*, 5937–5940. https://doi.org/10.1109/igarss46834.2022.9883463
- Forati, A. M., & Ghose, R. (2020). Volunteered geographic information users contributions pattern and its impact on information quality. *Preprints*. https://doi.org/10.20944/preprints202007.0270.v1
- Foody, G. M., See, L., Fritz, S., et al. (2015). Accurate attribute mapping from volunteered geographic information: Issues of volunteer quantity and quality. *The Cartographic Journal, 52*(4), 336–344. https://doi.org/10.1080/00087041.2015.1108658
- Goel, R., Miranda, J. J., Gouveia, N., et al. (2020). Using satellite imagery to estimate heavy vehicle volume for ecological injury analysis in India. *International Journal of Injury Control and Safety Promotion, 28*(1), 68–77. https://doi.org/10.1080/17457300.2020.1837886
- Gonçalves, A. P. (2023). *Map services management* [Master's thesis]. Instituto Superior de Engenharia do Porto. *(file: Downloads/Goncalves 2023 - Map Services Management.pdf; chưa có DOI — grey literature)*
- Gu, Z., Bapna, R., & Chan, J. (2022). Measuring the impact of crowdsourcing features on mobile app user engagement and retention: A randomized field experiment. *Management Science, 68*(2), 1297–1329. https://doi.org/10.1287/mnsc.2020.3943
- He, S., Bastani, F., Jagwani, S., et al. (2020). RoadTagger: Robust road attribute inference with graph neural networks. *Proceedings of the AAAI Conference on Artificial Intelligence, 34*(07), 10965–10972. https://doi.org/10.1609/aaai.v34i07.6730
- Jepsen, T. S., Jensen, C. S., & Nielsen, T. D. (2018). On network embedding for machine learning on road networks: A case study on the Danish road network. *IEEE Big Data 2018*, 3422–3431. https://doi.org/10.1109/bigdata.2018.8622416
- Jepsen, T. S., Jensen, C. S., & Nielsen, T. D. (2019). Graph convolutional networks for road networks. *ACM SIGSPATIAL 2019*, 460–463. https://doi.org/10.1145/3347146.3359094
- Jepsen, T. S., Jensen, C. S., & Nielsen, T. D. (2022). Relational fusion networks: Graph convolutional networks for road networks. *IEEE Transactions on Intelligent Transportation Systems, 23*(1), 418–429. https://doi.org/10.1109/tits.2020.3011799
- Keller, S., Gabriel, R., & Guth, J. (2020). Machine learning framework for the estimation of average speed in rural road networks with OpenStreetMap data. *ISPRS International Journal of Geo-Information, 9*(11), 638. https://doi.org/10.3390/ijgi9110638
- Li, J., Zhao, Y., & Song, S. (2024). Beyond navigation: Exploring users' contextual information needs and concerns when interacting with mobile map apps. *Proceedings of the Association for Information Science and Technology, 61*(1), 553–558. https://doi.org/10.1002/pra2.1057
- Lin, Y.-H., Chen, S.-Y., & Lin, P.-H. (2020). Assessing user retention of a mobile app: Survival analysis. *JMIR mHealth and uHealth, 8*(11), e16309. https://doi.org/10.2196/16309
- Liu, G., Zhang, D., Xu, C., Zhang, X., Zhang, Z., & Zhao, J. (2026). City-scale lane-level mapping from crowdsourced trajectories and satellite imagery. *IEEE Robotics and Automation Letters, 11*(4), 4793–4800. https://doi.org/10.1109/lra.2026.3664665
- Liu, M., Zhang, L., & Ge, J. (2020). Map matching for urban high-sampling-frequency GPS trajectories. *ISPRS International Journal of Geo-Information, 9*(1), 31. https://doi.org/10.3390/ijgi9010031
- Liu, Y., Shi, X., & Pierce, L. (2019). Characterizing and forecasting user engagement with in-app action graph. *ACM SIGKDD 2019*, 2023–2031. https://doi.org/10.1145/3292500.3330750
- Parker, C., May, A., & Mitchell, V. (2014). User-centred design of neogeography. *Ergonomics, 57*(7), 987–997. https://doi.org/10.1080/00140139.2014.909950
- Ratnamaheson, N. (2025). *A framework for on-demand creation of vector tiles for OpenStreetMap data* [Master's thesis]. University of Stuttgart, Institute of Formal Methods in Computer Science. *(file: Downloads/Ratnamaheson 2025 - MasterarbeitNR.pdf; chưa có DOI — grey literature)*
- Sevinç, H., Karaş, İ. R., & Demiral, E. (2020). Mobile-web-base volunteered geographic information application and geometric accuracy analysis for traffic accidents. *ISPRS Archives, XLIV-4/W3-2020*, 375–378. https://doi.org/10.5194/isprs-archives-xliv-4-w3-2020-375-2020
- Thanachan, P., & Jiamsanguanwong, A. (2016). Comparative usability evaluation of mobile map applications. *WCSE 2016*. https://doi.org/10.18178/wcse.2016.06.005
- Van Etten, A. (2019). City-scale road extraction from satellite imagery v2: Road speeds and travel times. *arXiv*. https://doi.org/10.48550/arxiv.1908.09715
- Yan, J., Ji, S., & Yao, W. (2022). A combination of convolutional and graph neural networks for regularized road surface extraction. *IEEE Transactions on Geoscience and Remote Sensing, 60*, 1–13. https://doi.org/10.1109/tgrs.2022.3151688
- Zhao, C., Guo, D., & Shao, C. (2024). SatDetX-YOLO: A more accurate method for vehicle target detection in satellite remote sensing imagery. *IEEE Access, 12*, 46024–46041. https://doi.org/10.1109/access.2024.3382245
