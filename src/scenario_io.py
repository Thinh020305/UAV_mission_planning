import json
import math
import os
import numpy as np
from fleet_analysis import drone_from_code, max_area_m2

R_EARTH = 6371008.8   # m

def project(lonlat, lon0, lat0):
    # Chiếu kinh/vĩ độ sang mét, phẳng quanh (lon0, lat0): x hướng đông, y hướng bắc
    a = np.asarray(lonlat, dtype=float)
    x = np.radians(a[:, 0] - lon0) * R_EARTH * math.cos(math.radians(lat0))
    y = np.radians(a[:, 1] - lat0) * R_EARTH
    return np.column_stack([x, y])

def unproject(xy, lon0, lat0):
    # Ngược lại của project: mét -> kinh/vĩ độ (dùng khi xuất kết quả về GeoJSON)
    a = np.asarray(xy, dtype=float)
    lon = lon0 + np.degrees(a[:, 0] / (R_EARTH * math.cos(math.radians(lat0))))
    lat = lat0 + np.degrees(a[:, 1] / R_EARTH)
    return np.column_stack([lon, lat])

def poly_area(xy):
    x, y = xy[:, 0], xy[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))

def rings(geom):
    # Trả về (các vòng ngoài, các vòng lỗ); mỗi vòng là mảng (n, 2) kinh/vĩ độ
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    outers, holes = [], []
    for p in polys:
        outers.append(np.asarray(p[0], dtype=float)[:, :2])
        holes.extend(np.asarray(r, dtype=float)[:, :2] for r in p[1:])
    return outers, holes

def read_scenario(path):
    with open(path, encoding="utf-8") as fh:
        fc = json.load(fh)
    area_f = [f for f in fc["features"] if (f.get("properties") or {}).get("type") != "Drone"]
    drones = [f for f in fc["features"] if (f.get("properties") or {}).get("type") == "Drone"]
    return fc, area_f[0]["geometry"], drones

def origin_of(geom):
    # Gốc tọa độ mét: trung bình các đỉnh vòng ngoài (cùng quy ước ở mọi hàm)
    outers, _ = rings(geom)
    allv = np.vstack(outers)
    return float(allv[:, 0].mean()), float(allv[:, 1].mean())

def geometry_metrics(geom, fleet_lonlat):
    # Diện tích (m2, đã trừ lỗ) và d_far (m): khoảng cách từ điểm xuất phát tới đỉnh xa nhất của vòng ngoài
    outers, holes = rings(geom)
    lon0, lat0 = origin_of(geom)
    area = sum(poly_area(project(r, lon0, lat0)) for r in outers) - sum(poly_area(project(r, lon0, lat0)) for r in holes)
    f = project(np.asarray(fleet_lonlat, dtype=float)[None, :2], lon0, lat0)[0]
    d_far = max(float(np.hypot(*(project(r, lon0, lat0) - f).T).max()) for r in outers)
    return dict(area_m2=area, d_far_m=d_far)

def compute_step1(geom, drone_feats, cap_footprint, gsd=0.02, overlap=0.5):
    gm = geometry_metrics(geom, drone_feats[0]["geometry"]["coordinates"])
    fleet = [drone_from_code(d["properties"]["model"]) for d in drone_feats]
    acd = [max_area_m2(d, gm["d_far_m"], gsd, overlap, cap_footprint=cap_footprint) for d in fleet]
    return gm, fleet, acd

def scenario_in_meters(path):
    # Đọc một file kịch bản và trả về mọi thứ đã ở hệ mét (x: đông, y: bắc), gốc tại origin_of(geom).
    # Dùng bản 'Updated' để surface_m2 đã trừ đoạn đi-về tới vùng.
    #   outers, holes: danh sách mảng (n, 2) mét (vòng đã khép kín như trong file)
    #   fleet_xy: điểm xuất phát chung của đội (2,)
    #   drones: danh sách dict(code, name, surface_m2) theo đúng thứ tự trong file
    #   origin: (lon0, lat0) để đổi ngược bằng unproject
    fc, geom, feats = read_scenario(path)
    lon0, lat0 = origin_of(geom)
    outers, holes = rings(geom)
    fleet_ll = np.asarray(feats[0]["geometry"]["coordinates"], dtype=float)[None, :2]
    gm = geometry_metrics(geom, feats[0]["geometry"]["coordinates"])
    return dict(
        name=os.path.basename(path), origin=(lon0, lat0),
        outers=[project(r, lon0, lat0) for r in outers],
        holes=[project(r, lon0, lat0) for r in holes],
        fleet_xy=project(fleet_ll, lon0, lat0)[0],
        drones=[dict(code=f["properties"]["model"], name=drone_from_code(f["properties"]["model"]).name,
                     surface_m2=f["properties"]["surface"]) for f in feats],
        area_m2=gm["area_m2"], d_far_m=gm["d_far_m"])

def to_shapely(sc):
    # Chuyển kịch bản (đã ở mét) sang đối tượng shapely: Polygon có lỗ, hoặc MultiPolygon
    from shapely.geometry import Polygon, MultiPolygon
    polys = []
    for o in sc["outers"]:
        po = Polygon(o)
        hs = [h for h in sc["holes"] if po.contains(Polygon(h).representative_point())]
        polys.append(Polygon(o, holes=hs))
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)

def load_step1(name, folder="step1_out"):
    # Lấy kết quả Bước 1 của một kịch bản: (dòng kịch bản, bảng UAV). name là tên file, ví dụ 'Achampet_India_fleet1.geojson'
    import pandas as pd
    S = pd.read_csv(f"{folder}/scenarios_step1.csv")
    D = pd.read_csv(f"{folder}/drones_step1.csv")
    return S[S.scenario == name].iloc[0], D[D.scenario == name].reset_index(drop=True)
