# Dữ liệu tối thiểu phục vụ mô phỏng

Audit đã thực thi trên 800 file: 100 tên vùng, 400 original và 400 convex hull, mỗi loại có fleet 5/10/15/20 UAV. Có đúng 800 feature Area và 10000 feature Drone. Tất cả Area là Polygon hợp lệ, nhiều nhất 4 lỗ. Không phát hiện feature vùng cấm riêng; lỗ được coi là vùng loại trừ. Không có khóa `(scenario, idx)` hoặc scenario bị trùng trong CSV.

| Đại lượng | Nguồn | Cách dùng |
|---|---|---|
| Miền gốc, holes | GeoJSON properties.type=Area | PODE/NPD, đối chiếu coverage |
| Miền hull | File `_convex_hull_` tương ứng | PDAN |
| Drone model, point, surface | Cùng FeatureCollection, properties.type=Drone | xác minh ID/index, giữ nguồn gốc |
| surface_updated_m2 | CSV Drone | đối chiếu với surface GeoJSON |
| acd_m2 | CSV Drone | giữ riêng để báo cáo, không làm target |
| requirement_m2 | CSV Drone | target area của từng UAV |
| not_assigned_m2 | CSV Scenario | đối chiếu residual geometry rồi tạo role UNASSIGNED |
| actual_area_m2 | Shapely output | tính sau phân vùng |

Sai khác surface CSV/GeoJSON lớn nhất = 0 m²; sai khác ACD và tổng surface theo scenario lớn nhất = 57804.31987979449 m². Vì vậy không đồng nhất chúng. Diện tích CSV/geometry và tổng requirements+NOT_ASSIGNED/geometry lệch lớn nhất khoảng 1.12e-8 m² do số học.

Loader dùng ID `UAV_{idx}` với idx bắt đầu 0, không dùng model làm ID. PDAN chọn cả geometry lẫn requirements của scenario hull để không dùng năng lực được tính cho miền khác. Metadata giữ đường dẫn input và computation, nguồn requirements và phần extra area.

Header thực tế đã lưu trong `outputs/audit/summary.json`, toàn bộ scenario tại `outputs/audit/data_audit.csv`, SHA256 tại `outputs/audit/manifest_sha256.json`. Dữ liệu được copy vào workspace; các tệp Desktop/Downloads không bị thay đổi.
