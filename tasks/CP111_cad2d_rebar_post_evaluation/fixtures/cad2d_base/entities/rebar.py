"""Rebar entities for reinforcement bar drawing."""
from __future__ import annotations
from typing import List, Optional

from ..geometry.point import Point2D
from .base import Entity


class LineRebar(Entity):
    """
    A line-type rebar (e.g., stirrup) with main body points and optional anchors.

    The rebar is represented as a polyline with distinct segments:
    - anchor_start: points forming the start anchor bend
    - body: main body of the rebar
    - anchor_end: points forming the end anchor bend

    Points are stored in order: [anchor_start..., body..., anchor_end...]
    """

    def __init__(
        self,
        points: List[Point2D],
        diameter: float = 8.0,
        anchor_start_count: int = 0,
        anchor_end_count: int = 0,
    ):
        super().__init__()
        self._points = list(points)
        self._diameter = diameter
        self._anchor_start_count = anchor_start_count
        self._anchor_end_count = anchor_end_count

    @property
    def points(self) -> List[Point2D]:
        return self._points

    @property
    def diameter(self) -> float:
        return self._diameter

    @property
    def anchor_start_count(self) -> int:
        """Number of points in the start anchor segment."""
        return self._anchor_start_count

    @property
    def anchor_end_count(self) -> int:
        """Number of points in the end anchor segment."""
        return self._anchor_end_count

    @property
    def body_points(self) -> List[Point2D]:
        """Points forming the main body (excluding anchors)."""
        start = self._anchor_start_count
        end = len(self._points) - self._anchor_end_count if self._anchor_end_count > 0 else len(self._points)
        return self._points[start:end]

    @property
    def anchor_start_points(self) -> List[Point2D]:
        """Points forming the start anchor."""
        if self._anchor_start_count == 0:
            return []
        return self._points[:self._anchor_start_count]

    @property
    def anchor_end_points(self) -> List[Point2D]:
        """Points forming the end anchor."""
        if self._anchor_end_count == 0:
            return []
        return self._points[-self._anchor_end_count:]

    def total_length(self) -> float:
        """Total rebar length including anchors."""
        total = 0.0
        for i in range(len(self._points) - 1):
            total += self._points[i].distance_to(self._points[i + 1])
        return total

    def accept(self, exporter):
        exporter.export_line_rebar(self)
