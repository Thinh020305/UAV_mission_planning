"""Adapter kiểm tra dữ liệu trên nền scenario_io, giữ nguyên module bước 1."""
from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
import pandas as pd
from shapely.geometry import shape
from shapely.ops import transform
import scenario_io as sio
from validation import tolerance

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Scenario:
    name: str
    path: Path
    domain: object
    original: object
    origin: tuple
    requirements: list
    drones: list
    audit: dict


def project_geometry(geometry, origin):
    lon0, lat0 = origin
    def forward(x, y, z=None):
        return (np.radians(np.asarray(x) - lon0) * sio.R_EARTH * math.cos(math.radians(lat0)),
                np.radians(np.asarray(y) - lat0) * sio.R_EARTH)
    return transform(forward, shape(geometry))


def geographic_geometry(geometry, origin):
    lon0, lat0 = origin
    def inverse(x, y, z=None):
        return (lon0 + np.degrees(np.asarray(x) / (sio.R_EARTH * math.cos(math.radians(lat0)))),
                lat0 + np.degrees(np.asarray(y) / sio.R_EARTH))
    return transform(inverse, geometry)


def checked_raw(path):
    fc, geom, drones = sio.read_scenario(str(path))
    if fc.get('type') != 'FeatureCollection':
        raise ValueError('Cần FeatureCollection')
    areas = [f for f in fc['features'] if (f.get('properties') or {}).get('type') == 'Area']
    unknown = [f for f in fc['features'] if (f.get('properties') or {}).get('type') not in ('Area', 'Drone')]
    if len(areas) != 1 or unknown or areas[0]['geometry'] != geom:
        raise ValueError('Schema chưa hỗ trợ: cần đúng một Area, Drone, không có feature chưa phân loại')
    if geom['type'] not in ('Polygon', 'MultiPolygon') or not drones:
        raise ValueError('Thiếu polygon/fleet')
    for drone in drones:
        props = drone['properties']
        if drone['geometry']['type'] != 'Point' or not {'model', 'surface'} <= props.keys():
            raise ValueError('Drone không đúng schema')
    return fc, geom, drones


def load_scenario(path, algorithm='npd', folder=ROOT / 'data'):
    path, folder = Path(path).resolve(), Path(folder)
    input_path = path
    # PDAN dùng đúng scenario hull và CSV hull đã tính bởi bước 1.
    if algorithm.lower() == 'pdan' and '_convex_hull_' not in path.name:
        hull_name = path.name.replace('_fleet', '_convex_hull_fleet')
        path = path.with_name(hull_name)
        if not path.exists():
            raise ValueError('PDAN cần file convex_hull kèm CSV bước 1 tương ứng; không tự tính lại fleet')
    _, geom, feats = checked_raw(path)
    sc = sio.scenario_in_meters(str(path))
    domain = sio.to_shapely(sc)
    direct = project_geometry(geom, sc['origin'])
    if not domain.is_valid or domain.symmetric_difference(direct).area > tolerance(domain.area):
        raise ValueError('to_shapely không giữ đúng cấu trúc rings hoặc hình học gốc invalid')
    original_path = path.with_name(path.name.replace('_convex_hull_', '_'))
    _, original_geom, original_feats = checked_raw(original_path)
    original = project_geometry(original_geom, sc['origin'])
    if not original.is_valid:
        raise ValueError('Original geometry invalid')
    if [f['properties']['model'] for f in original_feats] != [f['properties']['model'] for f in feats]:
        raise ValueError('Fleet original/hull không tương ứng')
    if algorithm.lower() == 'pdan' and domain.symmetric_difference(original.convex_hull).area > tolerance(domain.area):
        raise ValueError('Hull dataset khác convex hull của original')
    scenario_row, rows = sio.load_step1(path.name, str(folder))
    rows = rows.sort_values('idx')
    if list(rows.idx) != list(range(len(feats))):
        raise ValueError('CSV idx phải duy nhất và khớp thứ tự feature Drone')
    all_scenarios = pd.read_csv(folder / 'scenarios_step1.csv')
    if (all_scenarios.scenario == path.name).sum() != 1:
        raise ValueError('Scenario CSV không duy nhất')
    if abs(float(scenario_row.area_m2) - domain.area) > tolerance(domain.area):
        raise ValueError('Diện tích CSV và geometry không tương thích')
    drones, reqs, deltas = [], [], []
    for (_, row), feat in zip(rows.iterrows(), feats):
        if row.model != feat['properties']['model']:
            raise ValueError('CSV model không khớp index GeoJSON')
        values = [float(row[k]) for k in ('surface_updated_m2', 'acd_m2', 'requirement_m2')]
        if any(not math.isfinite(x) or x < 0 for x in values):
            raise ValueError('Giá trị fleet không hữu hạn hoặc âm')
        key = f'UAV_{int(row.idx)}'
        raw_surface = float(feat['properties']['surface'])
        deltas.append(values[0] - raw_surface)
        if abs(deltas[-1]) > max(1e-6, abs(raw_surface) * 1e-9):
            raise ValueError('surface CSV không khớp GeoJSON; xem audit trước khi chọn nguồn')
        drones.append(dict(drone_id=key, idx=int(row.idx), model=row.model,
                           surface_geojson_m2=raw_surface, surface_updated_m2=values[0],
                           acd_m2=values[1], requirement_m2=values[2],
                           sd_m=float(row.sd_m), cd_m=float(row.cd_m), agl_m=float(row.agl_m)))
        reqs.append((key, values[2]))
    residual = domain.area - sum(a for _, a in reqs)
    if residual < -tolerance(domain.area):
        raise ValueError('Tổng requirements vượt diện tích')
    expected = float(scenario_row.not_assigned_m2)
    if abs(residual - expected) > tolerance(domain.area):
        raise ValueError('NOT_ASSIGNED CSV khác residual geometry')
    if residual > tolerance(domain.area):
        reqs.append(('NOT_ASSIGNED', residual))
    elif reqs:
        # Chỉ hấp thụ sai số floating point của tổng CSV vào yêu cầu cuối, ghi rõ delta.
        reqs[-1] = (reqs[-1][0], reqs[-1][1] + residual)
    audit = dict(input_path=str(input_path), computation_path=str(path),
                 requirement_source='CSV requirement_m2', csv_area_m2=float(scenario_row.area_m2),
                 geometry_area_m2=domain.area, original_area_m2=original.area,
                 extra_area_m2=domain.difference(original).area,
                 floating_closure_delta_m2=residual if abs(residual) <= tolerance(domain.area) else 0,
                 acd_minus_surface_m2=sum(d['acd_m2'] - d['surface_updated_m2'] for d in drones),
                 surface_csv_geojson_max_delta_m2=max(map(abs, deltas)),
                 projection='scenario_io local equirectangular, R=6371008.8 m', origin=sc['origin'])
    return Scenario(input_path.name, path, domain, original, sc['origin'], reqs, drones, audit)
