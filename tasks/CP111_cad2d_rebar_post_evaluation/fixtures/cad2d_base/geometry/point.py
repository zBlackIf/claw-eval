"""Point2D - 2D point with basic operations."""
from __future__ import annotations
import math
from typing import Tuple


class Point2D:
    """2D point with arithmetic operations."""

    __slots__ = ('x', 'y')

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    def __repr__(self) -> str:
        return f"Point2D({self.x:.2f}, {self.y:.2f})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Point2D):
            return NotImplemented
        return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9

    def __hash__(self) -> int:
        return hash((round(self.x, 6), round(self.y, 6)))

    def __add__(self, other: Point2D) -> Point2D:
        return Point2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point2D) -> Point2D:
        return Point2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Point2D:
        return Point2D(self.x * scalar, self.y * scalar)

    def distance_to(self, other: Point2D) -> float:
        """Euclidean distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def translated(self, dx: float, dy: float) -> Point2D:
        return Point2D(self.x + dx, self.y + dy)

    def rotated(self, center: Point2D, angle_deg: float) -> Point2D:
        """Rotate around center by angle in degrees."""
        rad = math.radians(angle_deg)
        dx = self.x - center.x
        dy = self.y - center.y
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        return Point2D(
            center.x + dx * cos_a - dy * sin_a,
            center.y + dx * sin_a + dy * cos_a,
        )
