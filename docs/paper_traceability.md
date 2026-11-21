# Ánh xạ tài liệu và mã mô phỏng

Nguồn chính đã đọc: `references/main_paper.pdf` (34 trang), Section 3.1, 3.2, Figure 2, Section 3.4, 4.4.2; bản text lưu tại `references/main_paper.txt`. Figure 2 đã được render và xem ở `references/figure2_page.png`. [Trang nhà xuất bản](https://www.mdpi.com/2504-446X/9/12/816).

Định nghĩa nhãn: `PAPER_EXACT` là quy tắc xác nhận trong paper; `IMPLEMENTATION_CHOICE` là cách cụ thể hóa hoặc lựa chọn backend; `APPROXIMATION` là chuyển đổi số học/khác biệt mô hình. Nhãn `PAPER_EXACT` của một bước không khẳng định toàn bộ kết quả thí nghiệm được tái hiện chính xác.

| Bước | Nguồn đối chiếu | Mã project | Nhãn |
|---|---|---|---|
| Hai miền theo yêu cầu diện tích | Main §3.2, trang 8 | interface `split` | PAPER_EXACT |
| Sắp yêu cầu giảm dần, Greedy vào tổng nhỏ hơn | Main §3.2 | `balanced_strategy.greedy_groups` | PAPER_EXACT |
| Đệ quy tới một requirement/node | Main §3.2 và Figure 2, trang 9 | `balanced_partition` | PAPER_EXACT |
| Ví dụ grouping 45/55 | Figure 2 | `test_figure2_greedy_and_stable_ties` | PAPER_EXACT |
| Seed A với phần tử lớn nhất, hòa các bước sau chọn B, sort ổn định | Main không quy định tie; lựa chọn khớp Figure 2 | `greedy_groups` | IMPLEMENTATION_CHOICE |
| PODE non-convex/holes | Ref [32], repo chính thức pode | `splitters/pode.py` | IMPLEMENTATION_CHOICE: tích hợp source |
| PODE CDT + gộp convex pieces | Source pode `joined_constrained_delaunay_triangles` | `PODESplitter._split` | IMPLEMENTATION_CHOICE: chưa biết tùy chọn paper chính |
| NPD triangular mesh bottom-up | Ref [39], repo chính thức npd | `NPDSplitter._split` | IMPLEMENTATION_CHOICE: tích hợp source |
| NPD merge/swap/articulation/refinement | `npd/nonconvex.py`, commit lưu bên dưới | backend nguyên trạng | IMPLEMENTATION_CHOICE: source-backed, chưa xác nhận đồng nhất paper |
| Steiner count 25 | Main §3.2 không quy định | constructor + CLI | IMPLEMENTATION_CHOICE |
| PDAN chỉ convex, chạy hull | Main §3.2, Ref [33] | loader + `PDANSplitter` | PAPER_EXACT cho miền hull |
| PDAN analytic tối thiểu perimeter phần nhỏ | `pdan/pdan.py::minimizing_split`, `to_splitter` | `PDANSplitter._split` | IMPLEMENTATION_CHOICE: key từ source tác giả |
| Đảo output khi target > 1/2 | NPD source giới hạn requirement <= 1/2 | `BaseSplitter.split` | IMPLEMENTATION_CHOICE |
| Compactness sqrt(area)/perimeter | Main §3.4 Eq (12), trang 14 | `metrics.compactness` | PAPER_EXACT |
| Dùng requirements từ CSV bước 1 | Dữ liệu người dùng cung cấp | `data_loader.load_scenario` | IMPLEMENTATION_CHOICE |
| Projection equirectangular local | Module scenario_io được cung cấp | giữ nguyên + adapter | APPROXIMATION so với diện tích ellipsoid |
| Fraction từ tọa độ float và tỷ lệ area | Gon/source dùng Fraction, GEOS dùng float | `splitters/base.py` | APPROXIMATION số học khi về GEOS |
| NOT_ASSIGNED tham gia cây như requirement phụ | Main §3.1 giữ phần không được phủ; vị trí trong cây chưa mô tả đủ | loader, strategies | IMPLEMENTATION_CHOICE |
| Coverage từ giao union vùng được giao với original | Yêu cầu mô phỏng area decomposition | `partition_engine` | IMPLEMENTATION_CHOICE; không phải Eq (15) ảnh chụp |
| MultiPolygon component ordering | Source hỗ trợ Polygon | `BaseSplitter.split` | IMPLEMENTATION_CHOICE: extension, không gán là thuật toán paper |
| Sequential tăng dần dùng chung cho ba splitter | Source `npd.npd.split` dùng sorted(requirements) | `sequential_strategy` | IMPLEMENTATION_CHOICE cho so sánh |
| B_PODE | Main §4.4.2 đánh giá Balanced cho NPD/PDAN | metadata experiment=extension | IMPLEMENTATION_CHOICE: mở rộng |

## Phiên bản và provenance

- PODE 0.4.10: [repository của tác giả](https://github.com/GeorgySk/pode). Dùng backend nguyên trạng, không nhận là bản chính xác mà bài 2025 đã chạy.
- PDAN 0.1.9: [repository của tác giả](https://github.com/GeorgySk/pdan), API `minimizing_split` đã đọc trong mã package.
- NPD 0.3.0: [repository của tác giả](https://github.com/GeorgySk/npd), commit `1f4fae3ee0b291f328e90fb2a0660e1fd4750a4d`, snapshot ở `references/npd_source`. Changelog ghi 2026-11-15, sau thời điểm paper; không khẳng định đồng nhất với bản 2025.
- Ref [32]: [DOI 10.1177/1729881421989551](https://doi.org/10.1177/1729881421989551).
- Ref [33]: [DOI 10.1109/ACCESS.2021.3134760](https://doi.org/10.1109/ACCESS.2021.3134760).
- Ref [39]: [DOI 10.1109/ACCESS.2025.3525800](https://doi.org/10.1109/ACCESS.2025.3525800).

Đã đọc mã chính thức của ba thuật toán để triển khai, chưa đọc đủ toàn văn ba bài gốc để chứng minh mỗi công thức và lựa chọn của các bản package trùng paper. Dùng mã tác giả là căn cứ mô phỏng, không thay cho bằng chứng tái hiện chính xác toàn bộ nghiên cứu.
