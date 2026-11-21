"""Adapter PDAN analytical perimeter minimization từ mã tác giả."""
from pdan import minimizing_split
from .base import BaseSplitter


class PDANSplitter(BaseSplitter):
    name = 'pdan'
    def _split(self, polygon, target):
        if polygon.holes or not polygon.is_convex:
            raise ValueError('PDAN chỉ nhận convex Polygon không lỗ')
        return minimizing_split(polygon.border, target, key=lambda x, _: x.length)
