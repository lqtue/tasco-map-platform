# wiki/ — Bộ Wiki Luật Internal

Internal reference wiki cho workstream **Enrichment** (maxspeed / name): ánh xạ **Thông tư
38/2024/TT-BGTVT** sang OSM tags, bảng quyết định, và ví dụ thực tế. Đây là tài liệu tra cứu cho
operator và **input cho decision tree của Tuệ**.

Markdown ở đây là **source of truth** (diffable, cập nhật được) — được publish lên Confluence qua
`../../scripts/confluence_publish.py`. PDF gốc giữ lại làm bản render.

| File | Confluence page | Nội dung |
|---|---|---|
| [`01-bo-wiki-luat-internal.md`](01-bo-wiki-luat-internal.md) | *OSM Luật Internal — Wiki* | §1.1 luật→tốc độ · §1.2 hình thái→tag · §1.3 urban/rural · §1.4 6 nhóm xe · §1.5 oneway 2W/4W · §1.6 flowchart |
| [`02-bang-quyet-dinh-theo-luat.md`](02-bang-quyet-dinh-theo-luat.md) | *Bảng Quyết Định theo Luật* | §2.1 decision matrix · §2.2 rural theo xe · §2.3 ví dụ A–F · sơ đồ 3 panel · refs · phụ lục ảnh |
| `internal_wiki_update_osm_v0.1.pdf` | — | Bản PDF gốc (rendered) |
| `assets/` | (uploaded as attachments) | 12 ảnh: flowchart, 3-panel, biển R.420/421, biển tốc độ, ví dụ đường, ảnh iD Editor |

## Cập nhật & publish

```bash
# 1. Sửa file .md (+ ảnh trong assets/ nếu cần)
# 2. Xem trước storage XHTML, không gọi API:
python3 ../../scripts/confluence_publish.py --dry-run
# 3. Publish (cần env: CONFLUENCE_BASE_URL / _EMAIL / _TOKEN / _SPACE_KEY):
python3 ../../scripts/confluence_publish.py
```

> Liên quan: kế hoạch triển khai operator → [`../traffic/maxspeed/plans/maxspeed-name-edit-plan.md`](../traffic/maxspeed/plans/maxspeed-name-edit-plan.md).
