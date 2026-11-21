"""Chuyển đổi Shapely <-> gon, kiểm chứng mọi phép chia của backend."""
from fractions import Fraction
import math
from time import perf_counter
from gon.base import Contour, Point, Polygon as GonPolygon
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from metrics import compactness
from validation import validate_partition


def to_gon(polygon):
    polygon = orient(polygon, sign=1)
    def contour(ring):
        return Contour([Point(Fraction(float(x)), Fraction(float(y))) for x, y in list(ring.coords)[:-1]])
    return GonPolygon(contour(polygon.exterior), [contour(h) for h in polygon.interiors])


def from_gon(polygon):
    if isinstance(polygon, Contour):
        polygon = GonPolygon(polygon)
    def coords(contour):
        return [(float(p.x), float(p.y)) for p in contour.vertices]
    return Polygon(coords(polygon.border), [coords(h) for h in polygon.holes])


class BaseSplitter:
    name = 'base'
    def split(self, polygon, target_area):
        started = perf_counter()
        if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
            raise ValueError('Polygon phải hợp lệ, không rỗng')
        if not math.isfinite(target_area) or not 0 <= target_area <= polygon.area:
            raise ValueError('target_area ngoài miền')
        if target_area == 0:
            return Polygon(), polygon, {'backend': self.name, 'boundary_case': True}
        if target_area == polygon.area:
            return polygon, Polygon(), {'backend': self.name, 'boundary_case': True}
        extension = False
        if isinstance(polygon, MultiPolygon):
            if self.name == 'pdan':
                raise ValueError('PDAN chỉ nhận convex Polygon không lỗ')
            # Extension rõ ràng: phân bổ component theo bounds; backend chỉ cắt component cuối.
            extension = True
            firsts, seconds, remaining = [], [], target_area
            for part in sorted(polygon.geoms, key=lambda g: g.bounds):
                if remaining <= 0:
                    seconds.append(part)
                elif remaining >= part.area:
                    firsts.append(part)
                    remaining -= part.area
                else:
                    a, b, _ = self.split(part, remaining)
                    firsts.append(a)
                    seconds.append(b)
                    remaining = 0
            first, second = unary_union(firsts), unary_union(seconds)
        elif isinstance(polygon, Polygon):
            source = to_gon(polygon)
            # Preserve the requested ratio while closing rational shoelace vs GEOS rounding.
            target = source.area * Fraction(target_area / polygon.area)
            swap = target > source.area / 2
            if swap:
                target = source.area - target
            first, second = self._split(source, target)
            first, second = from_gon(first), from_gon(second)
            if swap:
                first, second = second, first
        else:
            raise ValueError('Chỉ nhận Polygon hoặc MultiPolygon')
        validation = validate_partition(polygon, {'A': first, 'B': second},
                                        {'A': target_area, 'B': polygon.area - target_area})
        return first, second, dict(backend=self.name, source_backed=True,
                                  reproduction='SOURCE_BACKED_NOT_PAPER_EXACT',
                                  multipolygon_extension=extension,
                                  split_runtime_seconds=perf_counter() - started,
                                  split_area_error_m2=abs(first.area - target_area),
                                  first_compactness=compactness(first), second_compactness=compactness(second),
                                  validation=validation)
