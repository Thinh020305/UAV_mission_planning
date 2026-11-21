"""Adapter PODE chính thức: CDT + convex merging + Hert-Lumelsky."""
import pode
from .base import BaseSplitter


class PODESplitter(BaseSplitter):
    name = 'pode'
    def _split(self, polygon, target):
        ratio = target / polygon.area
        return pode.divide(polygon, [pode.Requirement(ratio), pode.Requirement(1 - ratio)],
                           convex_divisor=pode.joined_constrained_delaunay_triangles)
