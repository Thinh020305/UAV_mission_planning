import pytest
from shapely.geometry import box
from balanced_strategy import greedy_groups, balanced_partition
from sequential_strategy import sequential_partition
from karmarkar_karp_strategy import karmarkar_karp_groups, karmarkar_karp_partition
from splitters.pdan import PDANSplitter
from validation import validate_partition


def test_figure2_greedy_and_stable_ties():
    reqs = [('1', 10), ('2', 15), ('3', 20), ('4', 25), ('5', 30)]
    a, b = greedy_groups(reqs)
    assert a == [('5', 30), ('2', 15)]
    assert b == [('4', 25), ('3', 20), ('1', 10)]
    assert greedy_groups([('a', 1), ('b', 1), ('c', 1), ('d', 1)]) == ([('a', 1), ('d', 1)], [('b', 1), ('c', 1)])


def test_karmarkar_karp_balances_partition():
    reqs = [('1', 8), ('2', 7), ('3', 6), ('4', 5), ('5', 4)]
    a, b = karmarkar_karp_groups(reqs)
    assert abs(sum(area for _key, area in a) - sum(area for _key, area in b)) == 2
    assert {key for key, _area in a + b} == {key for key, _area in reqs}


@pytest.mark.parametrize('strategy', [balanced_partition, sequential_partition, karmarkar_karp_partition])
def test_unequal_zero_unassigned_and_identity(strategy):
    p = box(0, 0, 10, 10)
    reqs = [('same_model_0', 11), ('same_model_1', 18), ('zero', 0), ('NOT_ASSIGNED', 71)]
    trace = []
    result = strategy(p, reqs, PDANSplitter(), trace)
    assert set(result) == set(dict(reqs))
    assert result['zero'].is_empty
    validate_partition(p, result, dict(reqs))
    assert trace


@pytest.mark.parametrize('strategy', [balanced_partition, sequential_partition, karmarkar_karp_partition])
def test_invalid_requirements(strategy):
    for reqs in [[], [('a', 30)], [('a', 50), ('a', 50)], [('a', -10), ('b', 110)]]:
        with pytest.raises(ValueError):
            strategy(box(0, 0, 10, 10), reqs, PDANSplitter())
