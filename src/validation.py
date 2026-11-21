"""Kiểm tra bảo toàn hình học, không tự sửa hình học không hợp lệ."""
from itertools import combinations
from shapely.ops import unary_union


def tolerance(area):
    return max(1e-5, area * 1e-8)


def validate_partition(domain, regions, requirements=None, forbidden=None):
    tol = tolerance(domain.area)
    errors = []
    if not domain.is_valid or domain.is_empty or domain.area <= 0:
        raise ValueError('Miền phân vùng không hợp lệ hoặc rỗng')
    for key, region in regions.items():
        if not region.is_valid or region.geom_type not in ('Polygon', 'MultiPolygon'):
            errors.append(f'{key}: invalid/non-polygon geometry')
        if region.is_empty and requirements and requirements.get(key, 0) > tol:
            errors.append(f'{key}: vùng rỗng với yêu cầu dương')
        if requirements and abs(region.area - requirements[key]) > tol:
            errors.append(f'{key}: sai diện tích {region.area - requirements[key]}')
    overlap = sum(a.intersection(b).area for a, b in combinations(regions.values(), 2))
    union = unary_union(list(regions.values()))
    gap = domain.symmetric_difference(union).area
    forbidden_overlap = union.intersection(forbidden).area if forbidden is not None else 0.0
    if overlap > tol:
        errors.append(f'Chồng lấn: {overlap}')
    if gap > tol:
        errors.append(f'Sai hợp hình học: {gap}')
    if forbidden_overlap > tol:
        errors.append(f'Giao vùng cấm: {forbidden_overlap}')
    result = dict(valid=not errors, overlap_m2=overlap, symmetric_difference_m2=gap,
                  forbidden_overlap_m2=forbidden_overlap, tolerance_m2=tol, errors=errors)
    if errors:
        raise ValueError(str(result))
    return result
