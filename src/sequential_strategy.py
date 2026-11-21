"""Sequential: tăng dần theo source NPD, tie giữ index UAV."""
from shapely.geometry import Polygon
from balanced_strategy import check_requirements
from validation import validate_partition


def sequential_partition(polygon, requirements, splitter, trace=None):
    check_requirements(polygon, requirements)
    trace = [] if trace is None else trace
    result = {key: Polygon() for key, area in requirements if area == 0}
    ordered = sorted(((k, a) for k, a in requirements if a > 0), key=lambda r: r[1])
    remainder = polygon
    for key, area in ordered[:-1]:
        part, other, info = splitter.split(remainder, area)
        validate_partition(remainder, {'part': part, 'other': other},
                           {'part': area, 'other': remainder.area - area})
        trace.append(dict(drone_id=key, target_area_m2=area, **info))
        result[key], remainder = part, other
    if ordered:
        result[ordered[-1][0]] = remainder
    return result
