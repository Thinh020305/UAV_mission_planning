import math
from dataclasses import dataclass

@dataclass(frozen=True)
class Drone:
    name: str
    mfd_m: float      # tầm bay tối đa (m)
    speed: float      # m/s
    hfov: float       # độ
    vfov: float       # độ
    hir: int          # độ phân giải ngang (px)
    vir: int          # độ phân giải dọc (px)

# Bảng 1 của bài báo (một số giá trị là xấp xỉ theo tác giả).
# Yuneec H520E: dùng HIR = 5472 (khớp Bảng 2 và dữ liệu Zenodo); Bảng 1 ghi 4864 là chép nhầm từ Phantom.
DRONES = [
    Drone("Parrot Anafi AI",     22500, 14.0,   64.6, 50.7, 8000, 6000),
    Drone("DJI Mini 4 Pro",      18000, 11.3,   69.7, 55.1, 8064, 6048),
    Drone("DJI Phantom 4 Pro",   18630, 10.35,  71.5, 56.7, 4864, 3648),
    Drone("DJI Air3",            22080, 8.0,    69.6, 55.0, 8064, 6048),
    Drone("Skydio X2E",          20000, 8.3,    67.7, 53.4, 4056, 3040),
    Drone("Skydio X10",          36000, 15.0,   80.2, 64.6, 8192, 6144),
    Drone("Yuneec H520E",        17010, 10.125, 78.3, 62.8, 5472, 3648),
]
DRONE_BY_NAME = {d.name: d for d in DRONES}

# Mã mô hình trong dữ liệu Zenodo -> tên trong Bảng 1
MODEL_CODES = {"PrtAi": "Parrot Anafi AI", "DjiMn4P": "DJI Mini 4 Pro", "DjiPhm4P": "DJI Phantom 4 Pro",
               "DjiA3": "DJI Air3", "SkDX2E": "Skydio X2E", "SkDX10": "Skydio X10", "YncH520E": "Yuneec H520E"}

def drone_from_code(code):
    return DRONE_BY_NAME[MODEL_CODES[code]]

def altitude_agl(d, gsd=0.02, agl_max=120.0):
    # Công thức (3), cắt ở độ cao tối đa cho phép (bài báo: 120 m)
    raw = d.hir * gsd / (2 * math.tan(math.radians(d.hfov / 2)))
    return min(raw, agl_max), raw

def footprints(d, gsd=0.02, agl_max=120.0, cap_footprint=False):
    # Trả về (agl, hfp, vfp) theo công thức (2) và (6)
    agl, raw = altitude_agl(d, gsd, agl_max)
    h = agl if cap_footprint else raw
    hfp = 2 * h * math.tan(math.radians(d.hfov / 2))
    vfp = 2 * h * math.tan(math.radians(d.vfov / 2))
    return agl, hfp, vfp

def sweep_capture(d, gsd=0.02, overlap=0.5, agl_max=120.0, cap_footprint=False):
    # Công thức (4), (5): khoảng cách giữa hai đường quét (SD) và giữa hai lần chụp (CD)
    agl, hfp, vfp = footprints(d, gsd, agl_max, cap_footprint)
    return agl, hfp * (1 - overlap), vfp * (1 - overlap)

def max_area_m2(d, d_far_m=0.0, gsd=0.02, overlap=0.5, agl_max=120.0, cap_footprint=False):
    # Công thức (7) với tầm bay đã trừ đoạn đi-về tới điểm xa nhất của vùng
    _, sd, _ = sweep_capture(d, gsd, overlap, agl_max, cap_footprint)
    effective = max(d.mfd_m - 2.0 * d_far_m, 0.0)
    return sd * effective

def area_requirements(polygon_area_m2, acd_list):
    # Giảm tỉ lệ nếu dư năng lực; ngược lại thêm phần 'Not Assigned'
    total = sum(acd_list)
    if total >= polygon_area_m2:
        k = polygon_area_m2 / total
        return [a * k for a in acd_list], 0.0
    return list(acd_list), polygon_area_m2 - total

def fleet_summary(polygon_area_m2, d_far_m, fleet, gsd=0.02, overlap=0.5, agl_max=120.0, cap_footprint=False):
    acd = [max_area_m2(d, d_far_m, gsd, overlap, agl_max, cap_footprint) for d in fleet]
    req, not_assigned = area_requirements(polygon_area_m2, acd)
    rows = []
    for d, a, r in zip(fleet, acd, req):
        agl, sd, cd = sweep_capture(d, gsd, overlap, agl_max, cap_footprint)
        rows.append(dict(drone=d.name, agl_m=round(agl, 1), sd_m=round(sd, 2), cd_m=round(cd, 2),
                         max_area_ha=round(a / 1e4, 1), requirement_ha=round(r / 1e4, 1)))
    return rows, not_assigned, sum(acd) < polygon_area_m2     # cờ: đội không đủ năng lực phủ vùng
