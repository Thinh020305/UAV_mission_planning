# Mô phỏng phân vùng khảo sát cho đội UAV — Area Decomposition

Dự án mô phỏng **Section 3.2 (Area Decomposition)** của bài *Increasing Automation on Mission Planning for Heterogeneous Multi-Rotor Drone Fleets in Emergency Response*: chia một vùng khảo sát thành các vùng nhỏ cho đội UAV có năng lực khác nhau bằng **PODE, NPD, PDAN**, kết hợp **Balanced Strategy**.

Tài liệu này dành cho thành viên mới: đọc mục 1–3 để hiểu bài toán và dữ liệu, mục 4–5 để chạy, mục 6–7 để đọc kết quả.

## 1. Bài toán cần giải quyết

Cho một vùng khảo sát và một đội UAV, mỗi UAV có diện tích yêu cầu khác nhau do kết quả Fleet Analysis ở bước trước cung cấp. Cần xác định **UAV nào nhận phần nào của vùng khảo sát**, sao cho:

- Diện tích vùng được giao gần bằng diện tích yêu cầu của UAV.
- Các vùng không chồng lấn và cùng phần chưa giao bao phủ miền tính toán.
- Với miền gốc, các lỗ trong polygon được loại khỏi vùng phân công.
- Đánh giá hình dạng vùng bằng compactness và đo thời gian phân vùng.

Ví dụ minh họa: miền có diện tích 100 ha, ba UAV cần lần lượt 20, 30 và 40 ha. Kết quả gồm ba vùng tương ứng và một vùng `NOT_ASSIGNED` 10 ha. Nếu tổng yêu cầu vượt diện tích miền, loader báo lỗi. `NOT_ASSIGNED` là phần chưa được giao, không phải một UAV.

Phạm vi hiện tại là **phân vùng diện tích**. Dự án chưa tạo đường bay, waypoint, lịch bay hoặc mô phỏng UAV bay; chưa triển khai Path Planning ở Section 3.3.

Luồng xử lý:

```text
GeoJSON vùng khảo sát + đội UAV      CSV kết quả Fleet Analysis bước 1
                 \                    /
                  Kiểm tra và ghép dữ liệu
                            |
                Đổi tọa độ sang hệ mét cục bộ
                            |
             Chọn splitter PODE / NPD / PDAN
                            |
               Balanced hoặc Sequential
                            |
           Kiểm tra diện tích, chồng lấn, hợp vùng
                            |
             GeoJSON + CSV + hình PNG + trace JSON
```

## 2. Input: cần cung cấp những gì?

Một lần chạy cần **GeoJSON và hai CSV bước 1 tương ứng**. Chỉ truyền GeoJSON vào lệnh là đủ khi hai CSV đã có sẵn trong `data/`.

### 2.1. GeoJSON kịch bản

Ví dụ: `data/updated_input/Achampet_India_fleet1.geojson`.

File là `FeatureCollection`, gồm đúng một feature `Area` và các feature `Drone`:

| Thành phần | Trường chính | Ý nghĩa |
|---|---|---|
| Vùng khảo sát | `properties.type = "Area"` | Phân biệt feature vùng |
| Hình học vùng | `geometry.type = "Polygon"` | Biên ngoài và các vòng lỗ nếu có |
| UAV | `properties.type = "Drone"` | Phân biệt feature UAV |
| Mẫu UAV | `properties.model` | Ví dụ `YncH520E`, có thể trùng giữa nhiều UAV |
| Diện tích theo dữ liệu | `properties.surface` | Đối chiếu với `surface_updated_m2` trong CSV |
| Vị trí UAV | `geometry.type = "Point"` | Tọa độ đầu vào của UAV; hiện chưa dùng để tính đường bay |

Tọa độ GeoJSON theo thứ tự **[kinh độ, vĩ độ]**, không phải tọa độ mét. Loader chiếu sang hệ mét cục bộ trước khi phân vùng; GeoJSON đầu ra được chuyển lại kinh độ/vĩ độ. Diện tích trong CSV và phép tính dùng **m²**; hình PNG ghi diện tích theo **km²**.

Tên kịch bản có dạng `<tên_vùng>_fleet<nhóm>.geojson`. Trong dataset hiện có:

| Nhóm | Số UAV |
|---|---:|
| `fleet1` | 5 |
| `fleet2` | 10 |
| `fleet3` | 15 |
| `fleet4` | 20 |

`fleet1` là tên nhóm đội bay, không có nghĩa là một UAV. Dataset đã audit có 100 vùng, 400 kịch bản gốc và 400 bản convex hull. Các vùng trong dataset đều là Polygon; adapter còn có hỗ trợ MultiPolygon dưới dạng mở rộng.

### 2.2. `data/drones_step1.csv`: yêu cầu từng UAV

| Cột | Cách sử dụng |
|---|---|
| `scenario` | Tên file GeoJSON, bao gồm đuôi `.geojson` |
| `idx` | Chỉ số UAV từ 0, khớp thứ tự feature Drone trong GeoJSON |
| `model` | Phải khớp model của Drone tương ứng |
| `surface_updated_m2` | Phải khớp `surface` trong GeoJSON |
| `acd_m2` | Đại lượng từ Fleet Analysis được giữ để báo cáo |
| **`requirement_m2`** | **Diện tích mục tiêu thực sự dùng để phân vùng cho UAV** |
| `sd_m`, `cd_m`, `agl_m` | Thông số bước 1 được giữ trong kết quả để truy vết |

ID đầu ra là `UAV_0`, `UAV_1`, … theo `idx`. Không dùng `model` làm ID vì nhiều UAV có thể cùng model. Không tự thay `requirement_m2` bằng `surface` hoặc `acd_m2`.

### 2.3. `data/scenarios_step1.csv`: tổng hợp kịch bản

Các cột quan trọng: `scenario`, `fleet_size`, `area_m2`, `not_assigned_m2`. Các cột khác như `polygon`, `convex_hull`, `d_far_m`, các tổng diện tích và cờ thiếu năng lực giữ thông tin bước 1.

Loader kiểm tra diện tích GeoJSON với `area_m2` và kiểm tra:

```text
Tổng requirement_m2 của các UAV + not_assigned_m2 ≈ diện tích miền
```

Phần dư dương được tạo thành vùng `NOT_ASSIGNED`. Sai lệch rất nhỏ do số thực được xử lý theo dung sai. Các dữ liệu âm, không hữu hạn, chỉ số không khớp hoặc tổng yêu cầu vượt miền sẽ bị từ chối.

### 2.4. Input riêng cho PDAN

PDAN cần polygon lồi, không lỗ. Khi chọn kịch bản gốc, loader tự tìm file hull cùng thư mục, ví dụ:

```text
Input yêu cầu:  Achampet_India_fleet1.geojson
PDAN tính trên: Achampet_India_convex_hull_fleet1.geojson
```

PDAN dùng cả **hình học hull và các dòng CSV của kịch bản hull**. Do đó, khi chạy cả ba thuật toán, PODE/NPD dùng miền gốc còn PDAN dùng hull; requirements cũng có thể khác. Cần đọc `computation_scenario`, `input_geometry` và phần diện tích ngoài biên gốc khi so sánh.

## 3. Phân biệt thuật toán và chiến lược

**Thuật toán (splitter)** thực hiện một phép chia miền thành hai phần theo diện tích mục tiêu. **Chiến lược (strategy)** quyết định thứ tự và nhóm UAV để gọi splitter nhiều lần.

| Lựa chọn | Vai trò trong dự án |
|---|---|
| `pode` | Phân rã miền, dùng backend Hert–Lumelsky qua thư viện tác giả; hỗ trợ miền lõm và lỗ |
| `npd` | Phân rã tam giác rồi gom từ dưới lên; hỗ trợ miền lõm và lỗ; miền lồi được backend chuyển sang PDAN |
| `pdan` | Chia giải tích trên polygon lồi; pipeline dùng bản convex hull |
| `balanced` | Sắp yêu cầu giảm dần, gom thành hai nhóm có tổng tương đối cân bằng rồi chia đệ quy |
| `sequential` | Baseline: sắp yêu cầu tăng dần, lần lượt tách từng vùng khỏi phần còn lại |
| `karmarkar-karp` | Dùng thuật toán differencing Karmarkar-Karp để tạo hai nhóm cân bằng ở mỗi nút rồi chia đệ quy |

Ví dụ Balanced với yêu cầu 10%, 15%, 20%, 25%, 30%: bước đầu tạo nhóm `30+15=45%` và `25+20+10=55%`, rồi tiếp tục chia trong từng nhóm. Balanced cân bằng tổng yêu cầu giữa các nhánh, không ép mọi UAV nhận diện tích bằng nhau.

Ba splitter gọi mã công khai của tác giả qua adapter. Balanced được triển khai tại dự án theo Section 3.2, có kiểm tra grouping Figure 2. Xem [phân tích thuật toán](docs/algorithm_analysis.md) để đọc chi tiết.

## 4. Chuẩn bị môi trường

Các lệnh bên dưới dùng **PowerShell**, chạy tại thư mục gốc dự án `UAV`. Môi trường đã dùng để kiểm chứng là **Python 3.13**.

### Nếu đã có `.venv`

Chạy ngay cả ba thuật toán với Balanced trên Achampet fleet1:

```powershell
.\.venv\Scripts\python.exe scripts/simulate.py
```

### Nếu là thành viên mới hoặc cần cài lại

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe scripts/build_symba_fallback.py
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/simulate.py
```

Không cần activate môi trường vì các lệnh gọi trực tiếp Python trong `.venv`. Lệnh cài dependencies cần kết nối mạng và cần giữ thư mục `references/` đi kèm dự án.

Script `build_symba_fallback.py` chuẩn bị `symba==1.2.1` dùng backend Python có sẵn, tránh extension C tùy chọn trên Windows thiếu compiler. Script chỉ đổi cấu hình build, không đổi công thức tính. Mã NPD kèm license ở `references/npd_source`, commit `1f4fae3ee0b291f328e90fb2a0660e1fd4750a4d`.

## 5. Các lệnh chạy thường dùng

### 5.1. Chạy cả ba thuật toán

```powershell
.\.venv\Scripts\python.exe scripts/simulate.py --algorithm all
```

Tương đương lệnh không có tham số: dùng `Achampet_India_fleet1.geojson`, chiến lược `balanced`, xuất vào `outputs/simulation/`.

### 5.2. Đổi kịch bản, vẫn chạy cả ba thuật toán

```powershell
.\.venv\Scripts\python.exe scripts/simulate.py --scenario data/updated_input/Achampet_India_fleet2.geojson --algorithm all
```

Xem các kịch bản có sẵn:

```powershell
Get-ChildItem data/updated_input -Filter *.geojson
```

### 5.3. Chọn một thuật toán

```powershell
.\.venv\Scripts\python.exe scripts/simulate.py --algorithm npd
```

Thay `npd` bằng `pode` hoặc `pdan`. Để đồng thời chọn kịch bản và thuật toán:

```powershell
.\.venv\Scripts\python.exe scripts/simulate.py --scenario data/updated_input/Achampet_India_fleet2.geojson --algorithm npd
```

### 5.4. Lưu vào thư mục riêng cho từng lần chạy

```powershell
.\.venv\Scripts\python.exe scripts/simulate.py --scenario data/updated_input/Achampet_India_fleet2.geojson --algorithm all --output outputs/achampet_fleet2
```

**Nên dùng thư mục riêng khi cần lưu lịch sử.** Mỗi lần gọi CLI, `comparison.csv` và `failures.json` được viết lại theo lần chạy đó. Các tệp cùng tên kịch bản/thuật toán/chiến lược bị ghi đè; tệp của cấu hình khác từ lần trước vẫn có thể còn trong thư mục.

### 5.5. Chạy Sequential hoặc so sánh cả hai chiến lược

```powershell
.\.venv\Scripts\python.exe scripts/simulate.py --algorithm npd --strategy sequential --output outputs/npd_sequential
.\.venv\Scripts\python.exe scripts/compare_algorithms.py --scenario data/updated_input/Achampet_India_fleet1.geojson --output outputs/compare_achampet
```

Lệnh thứ hai chạy sáu cấu hình: 3 thuật toán × 2 chiến lược. Cũng có thể dùng `simulate.py --algorithm all --strategy all`.

### 5.6. Chạy thử một số kịch bản trong dataset

```powershell
.\.venv\Scripts\python.exe scripts/run_batch.py --algorithm all --strategy balanced --limit 2 --output outputs/batch_demo
```

Lệnh lấy hai kịch bản gốc đầu tiên theo tên đã sắp xếp; PDAN vẫn tự lấy hull tương ứng. Bỏ `--limit 2` để chạy toàn bộ danh sách; thời gian phụ thuộc dữ liệu và thuật toán. Batch mặc định bỏ các file hull khỏi danh sách input độc lập.

### 5.7. Tham số CLI

| Tham số | Giá trị / tác dụng |
|---|---|
| `--scenario PATH` | GeoJSON kịch bản; mặc định của `simulate.py` là Achampet fleet1 |
| `--algorithm` | `all`, `pode`, `npd`, `pdan`; mặc định `simulate.py`: `all` |
| `--strategy` | `all`, `balanced`, `sequential`, `karmarkar-karp`; mặc định `simulate.py`: `balanced` |
| `--output PATH` | Thư mục output; mặc định `simulate.py`: `outputs/simulation/` |
| `--data-folder PATH` | Thư mục chứa hai CSV bước 1; mặc định `data/` của dự án |
| `--steiner-points N` | Tham số NPD, mặc định 25; thay đổi có thể ảnh hưởng hình dạng và thời gian |
| `--no-figures` | Không tạo PNG mới; vẫn xuất GeoJSON, CSV và trace |
| `--input-folder PATH` | Thư mục GeoJSON cho `run_batch.py`, mặc định `data/updated_input/` |
| `--limit N` | Giới hạn số kịch bản, hữu ích khi chạy batch |
| `--include-hull-inputs` | Batch thêm các bản hull thành input độc lập cho các thuật toán |
| `--help` | Xem cú pháp của script |

Các script khác có mặc định riêng: `run_single.py` và `run_batch.py` dùng NPD/Balanced, output `outputs/`; `compare_algorithms.py` dùng cả ba thuật toán/cả hai chiến lược, output `outputs/`. `run_single.py` bắt buộc có `--scenario` và chỉ nhận một thuật toán, một chiến lược.

## 6. Output: nhận được những gì?

### 6.1. Thông báo terminal

Ví dụ minh họa, thời gian thực tế thay đổi theo máy và input:

```text
Achampet_India_fleet1.geojson: pode/balanced OK, 0.500s
Achampet_India_fleet1.geojson: npd/balanced OK, 4.600s
Achampet_India_fleet1.geojson: pdan/balanced OK, 0.300s
```

Nếu lỗi sẽ có `FAILED: ...`; CLI tiếp tục các cấu hình còn lại, lưu chi tiết trong `failures.json` và trả mã thoát 1 nếu có lỗi, 0 nếu tất cả thành công. Thời gian in sau `OK` là thời gian phân vùng, không gồm toàn bộ đọc dữ liệu và xuất tệp.

### 6.2. Cấu trúc tệp

Ví dụ bộ kết quả NPD/Balanced:

```text
outputs/simulation/
├── comparison.csv
├── failures.json
├── figures/
│   ├── Achampet_India_fleet1__npd__balanced.png
│   └── Achampet_India_fleet1__npd__balanced__tree.png
├── geojson/
│   ├── Achampet_India_fleet1__npd__balanced.geojson
│   └── Achampet_India_fleet1__npd__balanced__context.geojson
├── metrics/
│   ├── Achampet_India_fleet1__npd__balanced.csv
│   └── Achampet_India_fleet1__npd__balanced__regions.csv
└── traces/
    └── Achampet_India_fleet1__npd__balanced.json
```

Chạy cả ba thuật toán sẽ có thêm các bộ tên chứa `pode` và `pdan`. Tên tệp theo quy tắc `<kịch_bản>__<thuật_toán>__<chiến_lược>`; cây `__tree.png` chỉ được xuất cho Balanced.

| Tệp | Nội dung và cách đọc |
|---|---|
| `figures/*.png` | Hình phân vùng: mỗi UAV một màu, nhãn ID và diện tích; `NOT_ASSIGNED` xám gạch chéo; biên gốc đen, lỗ đỏ, phần mở rộng hull có ký hiệu riêng |
| `figures/*__tree.png` | Cây chia nhóm Balanced; các số là index UAV, mỗi node ghi diện tích |
| `geojson/*.geojson` | Feature cho từng vùng UAV và phần UNASSIGNED nếu có; properties chứa diện tích, model, chỉ số; metadata chứa báo cáo, audit và phiên bản thư viện |
| `geojson/*__context.geojson` | Lớp tham chiếu biên gốc, phần mở rộng hull và lỗ; không cộng lớp này vào diện tích phân công |
| `metrics/*__regions.csv` | Một dòng cho mỗi UAV hoặc NOT_ASSIGNED: diện tích mục tiêu/thực tế, sai số, compactness, số component và thông tin bước 1 |
| `metrics/<tên_cấu_hình>.csv` | Một dòng tổng hợp cho cấu hình đó |
| `traces/*.json` | Nhật ký phép chia: node/nhóm, diện tích, thông tin backend và kiểm tra hình học |
| `comparison.csv` | Tổng hợp các cấu hình trong lần gọi CLI, mở bằng Excel để so sánh |
| `failures.json` | Danh sách lỗi và traceback; `[]` khi không có lỗi |

Để xem nhanh, mở PNG trong `figures/`, sau đó đọc `comparison.csv` và `__regions.csv`. Có thể mở GeoJSON bằng phần mềm GIS để xem hình học và properties.

## 7. Hiểu các chỉ số và giới hạn kết quả

| Chỉ số | Ý nghĩa |
|---|---|
| `requested_area_m2` | Diện tích mục tiêu của vùng |
| `actual_area_m2` | Diện tích hình học sau phân vùng |
| `area_error_m2` | Trị tuyệt đối của chênh lệch diện tích thực tế và mục tiêu; càng gần 0 càng tốt |
| `relative_area_error` | Sai số diện tích chia diện tích mục tiêu; mã trả 0 khi mục tiêu bằng 0 |
| `compactness` | `sqrt(diện tích) / chu vi`, tính cả chu vi lỗ; hình vuông có giá trị 0.25; lớn hơn biểu thị vùng gọn hơn theo chỉ số này |
| `mean_compactness`, `min_compactness` | Trung bình/nhỏ nhất trên các UAV thật, loại NOT_ASSIGNED |
| `assigned_area_m2` | Tổng diện tích giao cho UAV trên miền tính toán |
| `unassigned_area_m2` | Diện tích NOT_ASSIGNED trên miền tính toán |
| `coverage_percent` | 100 × diện tích đã giao nằm trong vùng gốc / diện tích vùng gốc |
| `extra_area_m2` | Phần miền tính toán nằm ngoài vùng gốc |
| `assigned_outside_original_m2` | Phần đã giao UAV nhưng nằm ngoài vùng gốc |
| `runtime_seconds` | Thời gian thực hiện chiến lược phân vùng |
| `pipeline_seconds_before_export` | Thời gian từ đầu pipeline đến trước xuất tệp, chưa gồm vẽ/lưu kết quả |
| `valid`, `overlap_m2`, `symmetric_difference_m2`, `forbidden_overlap_m2` | Kết quả kiểm tra hợp lệ, chồng lấn, khép kín miền và giao với vùng loại trừ nếu áp dụng |
| `status`, `reproduction` | Trạng thái thực thi và nhãn mức độ tái hiện |

Các điểm cần nhớ khi đánh giá:

- `coverage_percent` đo **diện tích được giao**, chưa đo độ phủ ảnh chụp hoặc hiệu quả đường bay. Giá trị dưới 100% có thể do năng lực đội bay không đủ và có NOT_ASSIGNED.
- PDAN dùng hull nên có thể giao cả phần ngoài biên gốc và các lỗ gốc. Metadata ghi `hull_flight_safety_validated=false`. Cần xét miền và requirements thực tế trước khi kết luận thuật toán tốt hơn.
- Nhãn `OK_SOURCE_BACKED` cho biết cấu hình chạy thành công; `SOURCE_BACKED_NOT_PAPER_EXACT` cho biết dùng mã nguồn có đối chiếu nhưng chưa xác nhận tái tạo đúng thí nghiệm gốc.
- Balanced + PODE là cấu hình mở rộng của mô phỏng. Steiner count 25 của NPD là lựa chọn chạy local, chưa xác nhận là tham số của thí nghiệm bài chính.
- Dùng phép chiếu equirectangular cục bộ và dung sai `max(1e-5, area * 1e-8)` m². Sai số số thực rất nhỏ không đồng nghĩa lỗi phân vùng.
- Đã có kết quả sáu cấu hình trên Achampet fleet1 trong `outputs/`; không dùng chúng để tuyên bố đã thực nghiệm toàn bộ dataset. Hỗ trợ MultiPolygon là mở rộng adapter, dataset đã audit không có MultiPolygon.

## 8. Thêm kịch bản và xử lý lỗi thường gặp

Để thêm kịch bản mới, cần chuẩn bị GeoJSON đúng schema và kết quả Fleet Analysis bước 1 trong hai CSV. Tên `scenario`, thứ tự `idx`, model, surface, diện tích và tổng yêu cầu phải khớp. Muốn chạy PDAN phải có thêm GeoJSON hull và các dòng CSV hull tương ứng; với quy tắc loader hiện tại, dùng cặp tên `<vùng>_fleetN.geojson` và `<vùng>_convex_hull_fleetN.geojson`. Không chỉ sửa polygon rồi giữ nguyên CSV cũ.

`fleet_analysis.py` và `scenario_io.py` là module được giữ nguyên từ bước 1. Pipeline này đọc `requirement_m2` đã cung cấp, không tự tính lại Fleet Analysis khi chạy mô phỏng.

| Hiện tượng | Kiểm tra / cách xử lý |
|---|---|
| Không tìm thấy `.venv\Scripts\python.exe` | Đứng tại thư mục gốc dự án và thực hiện mục cài môi trường |
| `ModuleNotFoundError` | Cài requirements bằng đúng Python trong `.venv` |
| Lỗi build `symba` | Chạy script chuẩn bị fallback trước khi cài requirements |
| Thiếu CSV hoặc không tìm thấy scenario trong CSV | Kiểm tra `--data-folder` và tên `scenario`, bao gồm đuôi file |
| Lỗi idx/model/surface/diện tích không tương thích | Kiểm tra đồng bộ GeoJSON với kết quả bước 1; xem traceback trong `failures.json` |
| PDAN báo thiếu convex hull | Bổ sung file hull và CSV hull tương ứng |
| `UnicodeEncodeError` khi in tiếng Việt | Thêm `-X utf8` ngay sau Python, ví dụ `.\.venv\Scripts\python.exe -X utf8 scripts/simulate.py --help` |
| Không có PNG mới | Kiểm tra có dùng `--no-figures` và cấu hình có chạy thành công không |
| Thư mục có nhiều kết quả cũ | Dùng `--output` với thư mục riêng để đọc đúng một lần chạy |

## 9. Cấu trúc mã nguồn và tài liệu đọc thêm

| Đường dẫn | Vai trò |
|---|---|
| `data/updated_input/` | GeoJSON gốc và hull |
| `data/*_step1.csv` | Kết quả Fleet Analysis đã chuẩn bị |
| `scripts/simulate.py` | Điểm chạy chính, mặc định cả ba thuật toán với Balanced |
| `scripts/_cli.py` | Tham số chung, vòng chạy và ghi tổng hợp/lỗi |
| `scripts/run_single.py` | Một kịch bản, một thuật toán, một chiến lược |
| `scripts/compare_algorithms.py` | So sánh sáu cấu hình trên cùng kịch bản |
| `scripts/run_batch.py` | Chạy nhiều kịch bản |
| `scripts/audit_data.py` | Kiểm tra và tổng hợp dữ liệu |
| `src/data_loader.py` | Ghép dữ liệu, chọn hull, lấy requirements, kiểm tra input |
| `src/partition_engine.py` | Điều phối phân vùng, tính chỉ số và xuất kết quả |
| `src/splitters/` | Adapter PODE, NPD, PDAN và interface `split(polygon, target_area)` |
| `src/balanced_strategy.py`, `src/sequential_strategy.py` | Hai chiến lược gọi splitter |
| `src/validation.py`, `src/metrics.py` | Kiểm tra hình học và tính chỉ số |
| `src/visualization.py` | Vẽ phân vùng và cây Balanced |
| `src/fleet_analysis.py`, `src/scenario_io.py` | Module bước 1 được giữ nguyên |
| `tests/` | Kiểm tra loader, splitter, chiến lược và tích hợp |
| `references/` | Mã nguồn/package tham chiếu cần cho cài đặt |
| `outputs/` | Kết quả chạy và audit |

Tài liệu chi tiết:

- [Phân tích ba thuật toán và Balanced](docs/algorithm_analysis.md).
- [Ánh xạ dữ liệu và nguồn từng đại lượng](docs/data_mapping.md).
- [Đối chiếu paper với mã nguồn](docs/paper_traceability.md).
- [Phạm vi, giả định và giới hạn tái hiện](docs/reproduction_limitations.md).

