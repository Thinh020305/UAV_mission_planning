import math
import pytest
from shapely.geometry import Polygon, MultiPolygon, box
from splitters import SPLITTERS
from validation import validate_partition


SHAPES = {
    'rectangle': box(0, 0, 12, 8),
    'convex': Polygon([(0, 0), (10, 1), (13, 7), (5, 11), (-1, 5)]),
    'nonconvex': Polygon([(0, 0), (12, 0), (10, 4), (12, 8), (6, 7), (2, 10), (0, 6)]),
    'L': Polygon([(0, 0), (10, 0), (10, 3), (3, 3), (3, 10), (0, 10)]),
    'hole': Polygon([(0, 0), (12, 0), (12, 12), (0, 12)], [[(4, 4), (4, 7), (7, 7), (7, 4)]]),
    'many_vertices': Polygon([(10 * math.cos(i * math.tau / 24), 10 * math.sin(i * math.tau / 24)) for i in range(24)]),
    'near_degenerate': Polygon([(0, 0), (1e-5, 0), (10, 1e-5), (10, .01), (0, .01)]),
}


@pytest.mark.parametrize('algorithm', SPLITTERS)
@pytest.mark.parametrize('shape_name', SHAPES)
@pytest.mark.parametrize('ratio', [.17, .73])
def test_geometric_quality(algorithm, shape_name, ratio):
    p = SHAPES[shape_name]
    splitter = SPLITTERS[algorithm]()
    if algorithm == 'pdan' and (p.interiors or p.convex_hull.area - p.area > 1e-9):
        with pytest.raises(ValueError, match='convex'):
            splitter.split(p, p.area * ratio)
        return
    a, b, info = splitter.split(p, p.area * ratio)
    assert a.is_valid and b.is_valid and a.area > 0 and b.area > 0
    assert validate_partition(p, {'a': a, 'b': b}, {'a': p.area * ratio, 'b': p.area * (1-ratio)})['valid']
    assert a.difference(p).area < 1e-6
    assert info['source_backed']


@pytest.mark.parametrize('algorithm', SPLITTERS)
def test_invalid_and_boundary(algorithm):
    splitter = SPLITTERS[algorithm]()
    p = box(0, 0, 10, 10)
    for area in [-1, 101, float('nan')]:
        with pytest.raises(ValueError):
            splitter.split(p, area)
    assert splitter.split(p, 0)[0].is_empty
    assert splitter.split(p, 100)[1].is_empty
    with pytest.raises(ValueError):
        splitter.split(Polygon([(0, 0), (2, 2), (0, 2), (2, 0)]), 1)


@pytest.mark.parametrize('algorithm', ['pode', 'npd'])
def test_multipolygon_explicit_extension(algorithm):
    p = MultiPolygon([box(0, 0, 3, 3), box(5, 0, 9, 4)])
    a, b, info = SPLITTERS[algorithm]().split(p, 12)
    assert info['multipolygon_extension']
    validate_partition(p, {'a': a, 'b': b}, {'a': 12, 'b': 13})
