"""Chỉ số phân vùng; coverage là area allocation, chưa phải ảnh chụp."""
import math


def compactness(geometry):
    """Equation (12): sqrt(Area) / Perimeter, bao gồm chu vi lỗ."""
    return math.sqrt(geometry.area) / geometry.length if geometry.length else 0.0


def region_metrics(geometry, requested):
    error = abs(geometry.area - requested)
    return dict(actual_area_m2=geometry.area, requested_area_m2=requested,
                area_error_m2=error, relative_area_error=error / requested if requested else 0.0,
                compactness=compactness(geometry),
                components=len(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else int(not geometry.is_empty))
