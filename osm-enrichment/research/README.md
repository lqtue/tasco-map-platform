# Research Bibliography — OSM Traffic Data Enrichment System

Literature support for [`../PROJECT_PLAN.md`](../PROJECT_PLAN.md), retrieved via the scite
(Smart Citations) literature index. Every entry below was retrieved as its own record;
key numbers are quoted from open-access full text or Smart Citation snippets. Links use
`https://doi.org/{doi}`.

> **Scope note.** The proposal cites *"Hugo Nilsson, 2024"* for the claim that AI is strong
> at **detecting** lane markings/arrows but weaker than geometric/graph rules at **reasoning**
> about lane connectivity at complex intersections. That specific source is **not indexed in the
> peer-reviewed corpus** (it appears to be an unindexed thesis). The same claim is, however,
> directly and quantitatively supported by **RoadTagger (He et al., 2020)** — use that as the
> citable peer-reviewed anchor. See Problem 3.
>
> No retraction or editorial-concern notices were flagged on any paper listed here.

---

## Problem 1 — Speed limits (legal rules ⊕ Mapillary sign detection)

**Rule-based defaults are the right backbone; OSM `maxspeed` is genuinely sparse.**
- **Guth, J., Wursthorn, S., & Keller, S. (2020).** *Multi-parameter estimation of average speed
  in road networks using fuzzy control.* ISPRS IJGI, 9(1), 55. https://doi.org/10.3390/ijgi9010055
  — Confirms OSM "often lack[s] information about the average speed of a road" and that routing
  engines fall back to **OSM-Wiki per-country default speed limits (only ~24 countries defined)**
  plus road class. Validates the proposal's Method 1 (legal defaults by road class/area). Code on GitHub.

**Extracting real signs from street-level imagery (Mapillary) is established.**
- **Ajmar, A., Arco, E., & Boccardo, P. (2019).** *Updating a road network dataset exploiting the
  results of semantic segmentation techniques applied to street-level imagery.* Int. Arch.
  Photogramm. Remote Sens. Spatial Inf. Sci., XLII-2/W13, 1511–1517.
  https://doi.org/10.5194/isprs-archives-xlii-2-w13-1511-2019
  — Uses **Mapillary + OSM** to update road networks with traffic signs (incl. speed limits). Direct
  precedent for Method 2.

**The "European-trained recognizer misfires on VN signs" risk is real and addressable.**
- **Romijnders, R., Meletis, P., & Dubbelman, G. (2019).** *A domain-agnostic normalization layer
  for unsupervised adversarial domain adaptation.* IEEE WACV. https://doi.org/10.1109/wacv.2019.00203
  — Domain-adaptation technique for the exact cross-country shift the plan flags. *(closed access)*
- **Tusher, M. M. R., Al Farid, F., Kafi, H. M., et al. (2024).** *BanTrafficNet: Bangladeshi traffic
  sign recognition using a lightweight deep learning approach.* Research Square (preprint).
  https://doi.org/10.21203/rs.3.rs-4216970/v1
  — A close regional analog (South-Asian sign set, retrained lightweight model) for the "retrain on
  Vietnamese signs" task.
- **Ruiz, I., & Serrat, J. (2022).** *Hierarchical novelty detection for traffic sign recognition.*
  Sensors, 22(12), 4389. https://doi.org/10.3390/s22124389
  — Handles **unseen / out-of-distribution sign classes** — useful for VN signs absent from European
  training data and for routing odd detections to manual review.
- **Jaghouar, S., Gustafsson, H., & Mehlig, B. (2021).** *Improving traffic sign recognition by active
  search.* arXiv. https://doi.org/10.48550/arxiv.2111.14426

---

## Problem 2 — Detecting signalized intersections

**Detect + geolocate road objects (poles, lights) from street imagery, then place on the map.**
- **Zhang, C., Fan, H., & Li, W. (2021).** *Automated detecting and placing road objects from
  street-level images.* Computational Urban Science, 1, 18.
  https://doi.org/10.1007/s43762-021-00019-6
  — End-to-end detect→geolocate→place pipeline for street furniture; template for the signal-pole step.
- **Krylov, V. A., & Dahyot, R. (2019).** *Object geolocation from crowdsourced street level imagery.*
  Springer. https://doi.org/10.1007/978-3-030-13453-2_7
  — Triangulating an object's map position from multiple Mapillary views. *(closed access)*
- **Qiu, S., Psyllidis, A., & Bozzon, A. (2019).** *Crowd-mapping urban objects from street-level
  imagery.* ACM WWW. https://doi.org/10.1145/3308558.3313651

**Traffic-light detection specifically, and the satellite fallback for un-imaged intersections.**
- **Mentasti, S., Simsek, Y. C., & Matteucci, M. (2023).** *Traffic lights detection and tracking for
  HD map creation.* Frontiers in Robotics and AI, 10, 1065394.
  https://doi.org/10.3389/frobt.2023.1065394
  — Direct traffic-light detection/tracking for map building.
- **Wijnands, J. S., Zhao, H., Nice, K. A., et al. (2020).** *Identifying safe intersection design
  through unsupervised feature extraction from satellite imagery.* Computer-Aided Civil and
  Infrastructure Engineering, 35(7). https://doi.org/10.1111/mice.12623
  — Intersection structure analysis **from satellite** — supports Step-2 fallback when no street imagery.
- **Ng, V., & Hofmann, D. (2018).** *Scalable feature extraction with aerial and satellite imagery.*
  SciPy. https://doi.org/10.25080/majora-4af1f417-015
  — Large-scale feature extraction (incl. turn-lane markings) with **OSM-derived labels** — relevant to
  candidate-filtering and to Problem 3.

---

## Problem 3 — Lane count (AI detects ⊕ rules decide)  ★ keystone

- **He, S., Bastani, F., Jagwani, S., et al. (2020).** *RoadTagger: Robust road attribute inference
  with graph neural networks.* AAAI, 34(07), 10965–10972.
  https://doi.org/10.1609/aaai.v34i07.6730  *(open; arXiv: https://doi.org/10.48550/arxiv.1912.12408)*
  — **The peer-reviewed anchor for the proposal's central architecture argument.** Shows a pure CNN
  image classifier is fundamentally limited for lane counting (limited receptive field; can't tell a
  real lane-count change from a classifier error), and that adding a **graph neural network to
  propagate/reason along the road graph** fixes it:
  > "RoadTagger improves the inference accuracy of the **number of lanes from 71.8% to 77.2%**, and of
  > the road type from 89.1% to 93.1% … a reduction of the absolute lane detection error of 22.2%."
  This is exactly "AI sees, rules/graph reason." Cite this wherever the plan currently cites Nilsson.

- **Zang, A., Xu, R., Li, Z., et al. (2017).** *Lane boundary extraction from satellite imagery.* ACM
  SIGSPATIAL. https://doi.org/10.1145/3149092.3149093
  — Pixel-wise lane-marking extraction from ~30 cm satellite imagery; notes that **knowing the number
  of lanes as a prior** materially improves boundary geometry — argues for the rules↔detection feedback
  loop. (Echoes the plan's ≥30 cm/pixel requirement.)

- **Yan, J., Ji, S., & Yao, W. (2022).** *A combination of convolutional and graph neural networks for
  regularized road surface extraction.* IEEE TGRS, 60, 1–13. https://doi.org/10.1109/tgrs.2022.3151688
  — Independent confirmation that **CNN feature extraction + GNN reasoning** is the strong baseline for
  structured road attributes; benchmarks against RoadTagger.

- **Kasmi, A., Denis, D., & Aufrère, R. (2018).** *Map matching and lanes number estimation with
  OpenStreetMap.* IEEE ITSC, 2659–2664. https://doi.org/10.1109/itsc.2018.8569840
  — Lane-count estimation reaching **83.64%** by fusing GPS traces with OSM attributes — a non-imagery
  cross-check signal.

---

## Cross-cutting — OSM enrichment, data quality & road extraction

- **Vargas-Munoz, J. E., Srivastava, S., & Tuia, D. (2021).** *OpenStreetMap: Challenges and
  opportunities in machine learning and remote sensing.* IEEE Geosci. Remote Sens. Mag., 9(1).
  https://doi.org/10.1109/mgrs.2020.2994107  *(165 citing pubs — read first as the field survey)*
- **Mo, S., Shi, Y., Yuan, Q., et al. (2024).** *A survey of deep learning road extraction algorithms
  using high-resolution remote sensing images.* Sensors, 24(5), 1708.
  https://doi.org/10.3390/s24051708  *(current state-of-the-art survey)*
- **Usmani, M., Bovolo, F., & Napolitano, M. (2023).** *Remote sensing and deep learning to understand
  noisy OpenStreetMap.* Remote Sensing, 15(18), 4639. https://doi.org/10.3390/rs15184639
- **Xie, X., Zhou, Y., & Xu, Y. (2019).** *OpenStreetMap data quality assessment via deep learning and
  remote sensing imagery.* IEEE Access, 7. https://doi.org/10.1109/access.2019.2957825
- **Almendros-Jiménez, J. M., & Becerra-Terón, A. (2018).** *Analyzing the tagging quality of the
  Spanish OpenStreetMap.* ISPRS IJGI, 7(8), 323. https://doi.org/10.3390/ijgi7080323
  — Methodology for measuring **completeness/consistency of OSM tags** — useful for the plan's periodic
  per-province quality reports.
- **Van Etten, A. (2019).** *City-scale road extraction from satellite imagery v2: Road speeds and
  travel times (CRESIv2).* arXiv. https://doi.org/10.48550/arxiv.1908.09715  *(also v1:
  https://doi.org/10.48550/arxiv.1904.09901)* — Inferring **speed/travel time** from extracted road
  graphs; relevant to both P1 and the routing-impact motivation.

---

## Follow-ups worth retrieving (cited within the above, not yet pulled)

- **Jepsen et al.** — GCN architecture for road attribute inference *including speed limit* (cited by
  Yan et al. 2022). High value for Problem 1's ML branch; retrieve and verify before citing.
- **Barrington-Leigh & Millard-Ball (2017)** — "40% of countries have ≥83% complete OSM street
  network" (cited by Sehra et al.); useful headline stat for the motivation section — retrieve to verify.
- The original **"Nilsson 2024"** thesis the plan references — locate the actual document (likely a
  university repository) if the exact source must be cited; otherwise substitute RoadTagger.

---

### How this maps to the plan's "Nhóm Bắt buộc" (mandatory) items

| Plan requirement | Supporting literature |
| :-- | :-- |
| Bảng tốc độ chuẩn theo luật VN (rule defaults) | Guth et al. 2020 |
| API Mapillary cho biển báo | Ajmar et al. 2019; Qiu et al. 2019 |
| Mẫu ngã tư đèn đỏ + phát hiện | Zhang et al. 2021; Mentasti et al. 2023; Wijnands et al. 2020 |
| Mẫu số làn + mô hình nhận diện | He et al. 2020 (RoadTagger); Zang et al. 2017; Yan et al. 2022 |
| Ngưỡng ảnh ≥30 cm/pixel | Zang et al. 2017 (30 cm WorldView); Van Etten 2019 |
| Domain gap (biển/vạch VN ≠ châu Âu) | Romijnders et al. 2019; Tusher et al. 2024; Ruiz & Serrat 2022 |
