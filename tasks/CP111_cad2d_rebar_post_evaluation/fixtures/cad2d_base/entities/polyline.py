"""Polyline entity for 2D drawings."""
from __future__ import annotations
from typing import List

from ..geometry.point import Point2D
from .base import Entity


class Polyline(Entity):
    """A polyline entity - sequence of connected line segments."""

    def __init__(self, points: List[Point2D], closed: bool = False):
        super().__init__()
        self._points = list(points)
        self._closed = closed

    @property
    def points(self) -> List[Point2D]:
        return self._points

    @property
    def closed(self) -> bool:
        return self._closed

    def accept(self, exporter):
        exporter.export_polyline(self)
