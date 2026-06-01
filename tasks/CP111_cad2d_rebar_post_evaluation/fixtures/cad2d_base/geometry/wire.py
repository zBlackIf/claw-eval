"""Wire2D - 2D polyline/polygon representation."""
from __future__ import annotations
from typing import List, Tuple, Optional
import math

from .point import Point2D


class Wire2D:
    """
    2D wire (polyline or polygon).

    A wire is a sequence of vertices connected by edges.
    Can be open (polyline) or closed (polygon).
    """

    def __init__(self, vertices: List[Point2D], closed: bool = False):
        self._vertices = list(vertices)
        self._closed = closed

    @property
    def vertices(self) -> List[Point2D]:
        return self._vertices

    @property
    def is_closed(self) -> bool:
        return self._closed

    @property
    def num_vertices(self) -> int:
        return len(self._vertices)

    @property
    def num_edges(self) -> int:
        n = len(self._vertices)
        if n < 2:
            return 0
        return n if self._closed else n - 1

    def edge(self, index: int) -> Tuple[Point2D, Point2D]:
        """Get edge by index as (start, end) pair."""
        n = len(self._vertices)
        return (self._vertices[index % n], self._vertices[(index + 1) % n])

    def length(self) -> float:
        """Total wire length."""
        total = 0.0
        for i in range(self.num_edges):
            p1, p2 = self.edge(i)
            total += p1.distance_to(p2)
        return total

    def centroid(self) -> Point2D:
        """Centroid of the vertices."""
        if not self._vertices:
            return Point2D(0, 0)
        cx = sum(v.x for v in self._vertices) / len(self._vertices)
        cy = sum(v.y for v in self._vertices) / len(self._vertices)
        return Point2D(cx, cy)

    def bounding_box(self) -> Tuple[Point2D, Point2D]:
        """Returns (min_corner, max_corner)."""
        if not self._vertices:
            return (Point2D(0, 0), Point2D(0, 0))
        xs = [v.x for v in self._vertices]
        ys = [v.y for v in self._vertices]
        return (Point2D(min(xs), min(ys)), Point2D(max(xs), max(ys)))

    def area(self) -> float:
        """Signed area using shoelface formula. Positive = CCW."""
        if not self._closed or len(self._vertices) < 3:
            return 0.0
        total = 0.0
        n = len(self._vertices)
        for i in range(n):
            j = (i + 1) % n
            total += self._vertices[i].x * self._vertices[j].y
            total -= self._vertices[j].x * self._vertices[i].y
        return total / 2.0
