# Ba thuật toán và Balanced Strategy

## Bài toán chung

Section 3.2 nhận miền khảo sát P và danh sách yêu cầu diện tích `(id_i, a_i)`. Một splitter tạo hai vùng A, B với `Area(A)=target_area`, `Area(B)=Area(P)-target_area`. Mục tiêu là đạt yêu cầu diện tích và tạo vùng compact. Lỗ của miền gốc được giữ ngoài vùng phân công khi chạy PODE/NPD.

Trong mã, tất cả diện tích dùng m². `split()` trả `(first, second, info)`; `info` chứa sai số và kết quả kiểm tra. Các split kiểm tra tính hợp lệ, chồng lấn và `A ∪ B = P`, trước khi đệ quy.

Compactness đúng theo Equation (12) bài chính là `sqrt(Area(R))/Perimeter(R)`. Hình vuông có giá trị 0.25. Chu vi bao gồm cả biên lỗ. Chỉ số này được dùng để đánh giá đầu ra, không có nghĩa cả ba thuật toán đều tối ưu toàn cục cùng một objective.

## PODE — Hert–Lumelsky cải tiến

Nguồn [32] là Skorobogatov et al., 2021, DOI [10.1177/1729881421989551](https://doi.org/10.1177/1729881421989551). Project gọi package chính thức [GeorgySk/pode](https://github.com/GeorgySk/pode), phiên bản 0.4.10.

Polygon được biểu diễn bằng contour ngoài và các hole contours. Backend phân rã thành convex pieces bằng constrained Delaunay triangulation; tùy chọn được chọn ở đây tiếp tục gộp các tam giác kề nhau nếu hợp vẫn lồi (`joined_constrained_delaunay_triangles`). Sau đó dựng Region Adjacency Graph, định hướng đồ thị theo thứ tự xử lý, gán yêu cầu vào các phần lồi. Sweep/divide xử lý phần yêu cầu và phần dư, hợp các mảnh gắn với cùng yêu cầu.

PODE nhận requirements theo **tỷ lệ có tổng 1**, nên adapter đổi hai diện tích thành `target/Area(P)` và phần bù. Không dùng một phép cắt đứng tự viết thay thế thuật toán. Không khẳng định PODE phiên bản này thực hiện tìm kiếm compactness toàn cục. Cách tạo convex pieces ảnh hưởng hình dạng đường chia; đây là một lựa chọn triển khai cần công bố.

Điều kiện dừng: backend phân bổ xong cả hai requirements. Backend hỗ trợ non-convex và holes. Những chi tiết chính nằm trong package: `pode/pode.py::divide`, `to_graph`, `Graph.from_undirected`, `pode/utils.py`.

## NPD — bottom-up

Nguồn [39]: Skorobogatov, Calvo, Barrado, Salamí, *Compact Workspace Decomposition Based on a Bottom-Up Approach*, IEEE Access 2025, DOI [10.1109/ACCESS.2025.3525800](https://doi.org/10.1109/ACCESS.2025.3525800). Dùng mã chính thức [GeorgySk/npd](https://github.com/GeorgySk/npd) tại commit đã lưu trong README.

Các bước đã đối chiếu trực tiếp từ mã tác giả:

1. Với convex polygon không lỗ, backend gọi PDAN để chia.
2. Với non-convex polygon, tính khoảng cách Steiner `delta=sqrt(Area(P)/steiner_points_count)`; thêm điểm ở trong miền và trên các cạnh, bao gồm cạnh lỗ.
3. Tạo constrained Delaunay triangulation và quan hệ kề theo cạnh; mỗi triangle ban đầu là một chunk.
4. Lấy nhóm chunk có ít triangles nhất; ưu tiên source có compactness thấp nhất và chọn hàng xóm sao cho union compactness lớn nhất. Gộp từng cặp và lặp.
5. Khi mọi chunk có ít nhất 5 triangles, mã hiện tại có bước `swap_leaves` để cải thiện phân bố.
6. Điều kiện tìm chunk ban đầu trong source là `requirement - area <= 2*area - requirement >= 0`, tương đương `2r/3 <= area <= r`. Không rút gọn sai điều kiện này thành quy tắc gom ô tùy ý.
7. Gộp những chunk còn nhỏ, chọn chunk không là articulation sao cho **min(compactness(chunk), compactness(remainder))** lớn nhất.
8. Dời triangle giữa hai vùng rồi tinh chỉnh triangle biên để đạt đúng diện tích yêu cầu.

Backend yêu cầu target không quá nửa diện tích. Adapter chọn chia yêu cầu nhỏ hơn rồi đảo hai output khi target ban đầu lớn hơn nửa. `steiner_points_count=25` là tham số mô phỏng do project chọn, không phải tham số đã xác nhận của thí nghiệm bài chính. CLI cho phép đổi bằng `--steiner-points`.

Các module nguồn: `npd/npd.py`, `npd/nonconvex.py`, `npd/structures.py`. Constructor Partition ghi chi phí O(n²); không suy rộng con số này thành độ phức tạp tổng của toàn thuật toán. Mô phỏng dùng nguyên quy tắc của mã nguồn, chưa chứng minh mọi chi tiết commit 2026 trùng bản thí nghiệm 2025.

## PDAN — analytical decomposition

Nguồn [33]: Skorobogatov, Barrado, Salamí, *Multi-Robot Workspace Division Based on Compact Polygon Decomposition*, IEEE Access 2021, DOI [10.1109/ACCESS.2021.3134760](https://doi.org/10.1109/ACCESS.2021.3134760). Dùng mã chính thức [GeorgySk/pdan](https://github.com/GeorgySk/pdan), phiên bản 0.1.9.

PDAN nhận convex polygon không lỗ. Backend xét các cặp cạnh biên (`domain`, `countersegment`) khả thi theo yêu cầu diện tích. Nó tách phần diện tích đã được xác định bởi những đỉnh nằm giữa hai cạnh, rồi giải bài toán phần diện tích còn lại trong miền giới hạn bởi cặp cạnh. Công thức analytic được chia theo trường hợp: hai cạnh thẳng đứng, một cạnh thẳng đứng, các cạnh song song nghiêng, trường hợp tổng quát. `to_splitter` tính đoạn phân chia; `minimizing_split` đánh giá các contour ứng viên và chọn contour có perimeter nhỏ nhất theo `key=lambda first, second: first.length`.

Adapter luôn đưa target nhỏ hơn hoặc bằng nửa vào backend và giữ đúng ánh xạ output. Không dùng binary search theo góc cố định để giả làm PDAN. Tọa độ chuyển sang Fraction trước khi gọi; các số radical của nghiệm được chuyển float khi trở lại Shapely và kiểm tra sai số.

Trong thiết lập Section 3.2, PDAN chạy trên convex hull. Vì vậy nó có thể phân vùng cả phần nằm ngoài polygon gốc và các lỗ gốc. Hình mô phỏng thể hiện riêng những phần này. `extra_area = convex_hull.area - original.area` khi original nằm trong hull.

## Balanced Strategy — phần đóng góp của Section 3.2

Mỗi lần đệ quy:

1. Sắp yêu cầu diện tích giảm dần.
2. Khởi tạo hai nhóm và tổng diện tích bằng 0.
3. Đưa phần tử lớn nhất vào A; lần lượt đưa phần tử còn lại vào nhóm có tổng nhỏ hơn, khi hòa chọn B. Giữ thứ tự input giữa các yêu cầu bằng nhau. Tie là lựa chọn triển khai để khớp grouping minh họa Figure 2.
4. Split polygon với target bằng tổng yêu cầu nhóm A.
5. Đệ quy trên hai vùng và hai nhóm. Khi nhóm còn một UAV, giao toàn bộ vùng cho UAV đó.

Ví dụ Figure 2 với `(10,15,20,25,30)%`: nhóm A là `30+15=45%`; nhóm B là `25+20+10=55%`. Sau đó A chia 30/15; B chia 25/(20+10); cuối cùng chia 20/10. Unit test kiểm tra đúng danh tính các phần tử trong hai nhóm.

Greedy không phải tìm partition tối ưu; không thay bằng subset-sum. Tại mỗi node, mã kiểm tra lại diện tích và hợp hình học. Với n requirements dương, có n lá và n−1 lần split; chi phí bao gồm các splitter trên miền con, không mặc định là O(log n). Gom nhóm có chi phí O(k log k) cho node k requirements.

`NOT_ASSIGNED` có thể tham gia như một yêu cầu phụ để tổng diện tích khép kín, nhưng output role là UNASSIGNED và không được tính như UAV. Đây là lựa chọn của mô phỏng. Yêu cầu 0 trả vùng rỗng và không tạo node chia hình học vô nghĩa.

## Phạm vi kiểm chứng

Đã chạy cả ba splitter, Balanced và baseline Sequential trên một scenario thật. Các test bổ sung hình chữ nhật, lồi, lõm, chữ L, có lỗ, nhiều đỉnh, gần suy biến, yêu cầu không đều và MultiPolygon. Source gốc dùng Polygon; phân bổ qua nhiều component là extension của adapter, được đánh dấu trong trace. Những đầu vào không hợp lệ bị từ chối, không âm thầm `buffer(0)` hoặc lấp lỗ.
