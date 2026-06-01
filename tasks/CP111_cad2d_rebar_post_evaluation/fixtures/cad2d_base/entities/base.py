"""Entity - Base class for all drawing entities."""
from __future__ import annotations
from typing import Optional, Dict, Any, Tuple

from ..geometry.point import Point2D


class Entity:
    """
    Base class for all drawing entities.

    Provides common properties: layer, color, transform.
    Subclasses must implement accept(exporter) for the visitor pattern.
    """

    def __init__(self):
        self._layer: str = '0'
        self._color: Optional[int] = None
        self._linetype: Optional[str] = None

    @property
    def layer(self) -> str:
        return self._layer

    @layer.setter
    def layer(self, value: str):
        self._layer = value

    @property
    def color(self) -> Optional[int]:
        return self._color

    @color.setter
    def color(self, value: Optional[int]):
        self._color = value

    def accept(self, exporter):
        """Visitor pattern dispatch to exporter."""
        raise NotImplementedError
