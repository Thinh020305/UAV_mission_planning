"""Chien luoc phan chia bang thuat toan differencing Karmarkar-Karp."""
import heapq
import math

from shapely.geometry import Polygon

from balanced_strategy import check_requirements
from validation import validate_partition


def karmarkar_karp_groups(requirements):
    if len(requirements) < 2:
        raise ValueError('Cần ít nhất hai yêu cầu')
    keys = [key for key, _area in requirements]
    if len(set(keys)) != len(keys):
        raise ValueError('Danh sách rỗng hoặc ID trùng')
    if any(not math.isfinite(area) or area < 0 for _key, area in requirements):
        raise ValueError('Diện tích phải hữu hạn, không âm')

    heap = []
    for index, (_key, area) in enumerate(requirements):
        heapq.heappush(heap, (-area, index, frozenset((index,)), frozenset()))

    while len(heap) > 1:
        first_weight, first_order, first_plus, first_minus = heapq.heappop(heap)
        second_weight, second_order, second_plus, second_minus = heapq.heappop(heap)
        weight_a, weight_b = -first_weight, -second_weight

        if weight_a >= weight_b:
            new_plus = first_plus | second_minus
            new_minus = first_minus | second_plus
            difference = weight_a - weight_b
        else:
            new_plus = second_plus | first_minus
            new_minus = second_minus | first_plus
            difference = weight_b - weight_a

        heapq.heappush(
            heap,
            (-difference, min(first_order, second_order), new_plus, new_minus),
        )

    _weight, _order, plus_indices, minus_indices = heap[0]
    plus = [item for index, item in enumerate(requirements) if index in plus_indices]
    minus = [item for index, item in enumerate(requirements) if index in minus_indices]
    if not plus or not minus:
        ordered = sorted(requirements, key=lambda item: -item[1])
        middle = len(ordered) // 2
        plus = ordered[:middle]
        minus = ordered[middle:]
    return plus, minus


def karmarkar_karp_partition(polygon, requirements, splitter, trace=None):
    check_requirements(polygon, requirements)
    trace = [] if trace is None else trace
    result = {key: Polygon() for key, area in requirements if area == 0}

    def visit(region, reqs, node):
        if len(reqs) == 1:
            result[reqs[0][0]] = region
            trace.append(dict(node=node, ids=[reqs[0][0]], area_m2=region.area, leaf=True))
            return

        a, b = karmarkar_karp_groups(reqs)
        target = sum(area for _key, area in a)
        first, second, info = splitter.split(region, target)
        validate_partition(
            region,
            {'A': first, 'B': second},
            {'A': target, 'B': region.area - target},
        )
        trace.append(
            dict(
                node=node,
                ids=[key for key, _area in reqs],
                area_m2=region.area,
                target_area_m2=target,
                leaf=False,
                method='karmarkar-karp',
                **info,
            )
        )
        visit(first, a, node + 'L')
        visit(second, b, node + 'R')

    positive = [(key, area) for key, area in requirements if area > 0]
    if positive:
        visit(polygon, positive, 'root')
    return result