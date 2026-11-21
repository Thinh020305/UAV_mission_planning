"""Adapter thuật toán bottom-up từ repository tác giả, không thay lưới vuông."""
from npd.npd import split_into_two
from .base import BaseSplitter


class NPDSplitter(BaseSplitter):
    name = 'npd'
    def __init__(self, steiner_points_count=25):
        if not isinstance(steiner_points_count, int) or steiner_points_count <= 0:
            raise ValueError('steiner_points_count phải là số nguyên dương')
        self.steiner_points_count = steiner_points_count

    def _split(self, polygon, target):
        return split_into_two(polygon, requirement=target,
                              steiner_points_count=self.steiner_points_count)
