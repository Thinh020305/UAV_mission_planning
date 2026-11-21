# Phạm vi và giới hạn mô phỏng

Theo yêu cầu thu gọn, sản phẩm tập trung ba splitter và Balanced Strategy của Section 3.2. Không chạy thí nghiệm toàn bộ dataset, không triển khai Section 3.3, không suy luận cải thiện đường bay từ kết quả phân vùng.

**Đã thực thi:** sáu cấu hình trên Achampet fleet1 với dữ liệu thật; GeoJSON, metrics, hình phân vùng và cây Balanced đã xuất. Các số trong `outputs/comparison.csv` là kết quả thực thi. Script `simulate.py` tập trung ba cấu hình Balanced theo phạm vi mới.

**Độ trung thực:** Balanced tái hiện quy tắc §3.2 và grouping Figure 2. Splitter gọi mã công bố của tác giả; phiên bản và tham số không được bài chính mô tả đủ nên dùng nhãn `SOURCE_BACKED_NOT_PAPER_EXACT`. Không có splitter thay thế tự chế được gắn tên PODE/NPD/PDAN.

**PODE:** chọn convex merging trước Hert–Lumelsky. Không có bằng chứng phiên bản/tùy chọn này trùng cấu hình của thí nghiệm chính. Không tuyên bố splitter này tối ưu compactness toàn cục.

**NPD:** Steiner count=25 được chọn để mô phỏng chạy local; không phải giá trị xác nhận của tác giả bài chính. Snapshot 0.3.0 có changelog 2026, cần đối chiếu lịch sử nếu muốn tái tạo đúng bản 2025. Với polygon convex, mã nguồn NPD gọi PDAN.

**PDAN:** dùng file convex_hull có sẵn và yêu cầu CSV tương ứng. Lỗ và vùng ngoài biên gốc nằm trong miền hull có thể được giao UAV. Output ghi `hull_flight_safety_validated=false`. Không xem đây là phương án bay đã kiểm chứng an toàn.

**Số học:** projection của `scenario_io` là xấp xỉ equirectangular theo mét, gốc lấy trung bình các đỉnh exterior, kể cả đỉnh đóng vòng như source. Gốc hull và original khác nhau nên diện tích original tính trong khung hull hơi khác số m² ở CSV original. Mỗi lần đánh giá original/hull dùng chung khung tọa độ của lần chạy; không trộn hai diện tích. Fraction bảo toàn tọa độ float đầu vào của backend; output analytic trở về float và kiểm tra với dung sai `max(1e-5, area*1e-8)` m².

**Coverage:** chỉ đo diện tích đã được giao cho UAV thật trong polygon gốc. Không phải coverage ảnh chụp tại Equation (15) vì chưa lập đường bay hoặc footprint ảnh.

**MultiPolygon:** dataset thật có 800 Polygon, không có MultiPolygon. Adapter có extension phân bổ component theo bounds rồi cắt component cần thiết. Trace đánh dấu extension; không tuyên bố quy tắc component này nằm trong bài gốc.

**NOT_ASSIGNED:** xuất role UNASSIGNED; không tính trong fleet_size hay compactness trung bình UAV. Vị trí phần phụ trong cây Balanced là lựa chọn triển khai cần công bố.

**Fleet Analysis:** source gốc không sửa. Nhận thấy `footprints(cap_footprint=False)` dùng altitude raw cho footprint trong khi altitude_agl bị cap, và source có chú thích thay HIR Yuneec. Project không sửa các lựa chọn đó. Dùng nguyên requirement CSV đã được cung cấp; để nghiên cứu lại các giả định này cần trao đổi với thành viên phụ trách bước 1.

**Môi trường:** symba 1.2.1 có extension C không build được trên máy thiếu compiler. Script kèm theo chỉ tắt cấu hình build extension để dùng fallback Python có sẵn; mã tính toán không bị thay đổi. Có thể chậm hơn bản extension C.
