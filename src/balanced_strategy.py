"""Greedy và đệ quy theo Section 3.2; tie ổn định theo thứ tự đầu vào."""
import math
from shapely.geometry import Polygon
from validation import validate_partition, tolerance


def check_requirements(polygon, requirements):
    ids = [key for key, _ in requirements]
    if not requirements or len(set(ids)) != len(ids):
        raise ValueError('Danh sách rỗng hoặc ID trùng')
    if any(not math.isfinite(a) or a < 0 for _, a in requirements):
        raise ValueError('Diện tích phải hữu hạn, không âm')
    if abs(sum(a for _, a in requirements) - polygon.area) > tolerance(polygon.area):
        raise ValueError('Tổng requirements phải bằng diện tích miền')


def greedy_groups(requirements):
    if len(requirements) < 2:
        raise ValueError('Cần ít nhất hai yêu cầu')
    ordered = sorted(requirements, key=lambda r: -r[1])
    # Seed A with the largest item; subsequent ties go to B (Figure 2 grouping).
    groups, totals = [[ordered[0]], []], [ordered[0][1], 0.0]
    for item in ordered[1:]:
        index = 0 if totals[0] < totals[1] else 1
        groups[index].append(item)
        totals[index] += item[1]
    return groups[0], groups[1]


def balanced_partition(polygon, requirements, splitter, trace=None):
    check_requirements(polygon, requirements)
    trace = [] if trace is None else trace
    result = {key: Polygon() for key, area in requirements if area == 0}

    def visit(region, reqs, node):
        if len(reqs) == 1:
            result[reqs[0][0]] = region
            trace.append(dict(node=node, ids=[reqs[0][0]], area_m2=region.area, leaf=True))
            return
        a, b = greedy_groups(reqs)
        target = sum(x[1] for x in a)
        first, second, info = splitter.split(region, target)
        validate_partition(region, {'A': first, 'B': second},
                           {'A': target, 'B': region.area - target})
        trace.append(dict(node=node, ids=[x[0] for x in reqs], area_m2=region.area,
                          target_area_m2=target, leaf=False, **info))
        visit(first, a, node + 'L')
        visit(second, b, node + 'R')

    positive = [(key, area) for key, area in requirements if area > 0]
    if positive:
        visit(polygon, positive, 'root')
    return result
