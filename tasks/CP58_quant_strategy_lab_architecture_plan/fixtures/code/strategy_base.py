"""StrategyBase - Base class for quantitative trading strategies.

This module implements the core zero-cross detection system using
slow-face (慢面) zero-cross intervals at 1-hour timeframe as entry signals.

Current capabilities:
- 1-hour slow-face zero-cross interval detection
- Walk extension of target price segments based on sub-node structure
- Fine-grained entry/exit refinement via smaller timeframe zero-cross intervals

Planned (Strategy Lab):
- Strategy backtesting framework
- Parameter optimization
- Multi-timeframe signal combination
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class TimeFrame(Enum):
    M1 = "1min"
    M5 = "5min"
    M15 = "15min"
    M30 = "30min"
    H1 = "1hour"
    H4 = "4hour"
    D1 = "1day"


class Direction(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class ZeroCrossInterval:
    """Represents a slow-face zero-cross interval.

    A zero-cross interval is the period between two consecutive zero-crossings
    of the slow-face indicator. Direction is determined by the sign of the
    indicator during the interval.
    """
    timeframe: TimeFrame
    direction: Direction
    start_time: datetime
    end_time: Optional[datetime]
    start_price: float
    end_price: Optional[float]
    peak_price: Optional[float] = None
    sub_nodes: List["ZeroCrossInterval"] = field(default_factory=list)

    @property
    def duration_bars(self) -> int:
        if not self.end_time:
            return 0
        delta = self.end_time - self.start_time
        tf_minutes = {
            TimeFrame.M1: 1, TimeFrame.M5: 5, TimeFrame.M15: 15,
            TimeFrame.M30: 30, TimeFrame.H1: 60, TimeFrame.H4: 240,
            TimeFrame.D1: 1440,
        }
        return int(delta.total_seconds() / 60 / tf_minutes.get(self.timeframe, 60))

    @property
    def amplitude(self) -> float:
        if self.end_price and self.start_price:
            return abs(self.end_price - self.start_price) / self.start_price
        return 0.0


@dataclass
class PriceSegment:
    """A directional price movement segment derived from zero-cross intervals."""
    direction: Direction
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    source_interval: ZeroCrossInterval
    extended: bool = False  # Whether walk-extension was applied
    refinement_applied: bool = False  # Whether sub-timeframe refinement was applied


class StrategyBase:
    """Base strategy using 1-hour slow-face zero-cross detection."""

    def __init__(self):
        self.intervals_h1: List[ZeroCrossInterval] = []
        self.segments: List[PriceSegment] = []

    def detect_zero_cross(self, bars: list, timeframe: TimeFrame) -> List[ZeroCrossInterval]:
        """Detect zero-cross intervals from bar data.

        Args:
            bars: List of OHLCV bar dicts with 'slow_face' indicator value
            timeframe: The timeframe of the bars

        Returns:
            List of detected ZeroCrossInterval objects
        """
        intervals = []
        current_interval = None

        for bar in bars:
            slow_face = bar.get("slow_face", 0)
            timestamp = datetime.fromisoformat(bar["timestamp"])
            price = bar["close"]

            if current_interval is None:
                direction = Direction.LONG if slow_face >= 0 else Direction.SHORT
                current_interval = ZeroCrossInterval(
                    timeframe=timeframe,
                    direction=direction,
                    start_time=timestamp,
                    end_time=None,
                    start_price=price,
                    end_price=None,
                )
            else:
                # Check for zero crossing
                is_positive = slow_face >= 0
                was_positive = current_interval.direction == Direction.LONG

                if is_positive != was_positive:
                    # Zero crossing detected - close current interval
                    current_interval.end_time = timestamp
                    current_interval.end_price = price
                    intervals.append(current_interval)

                    # Start new interval
                    direction = Direction.LONG if is_positive else Direction.SHORT
                    current_interval = ZeroCrossInterval(
                        timeframe=timeframe,
                        direction=direction,
                        start_time=timestamp,
                        end_time=None,
                        start_price=price,
                        end_price=None,
                    )
                else:
                    # Update peak
                    if current_interval.peak_price is None:
                        current_interval.peak_price = price
                    elif current_interval.direction == Direction.LONG:
                        current_interval.peak_price = max(current_interval.peak_price, price)
                    else:
                        current_interval.peak_price = min(current_interval.peak_price, price)

        # Close last interval if open
        if current_interval and current_interval.end_time is None:
            current_interval.end_time = bars[-1]["timestamp"] if bars else None
            current_interval.end_price = bars[-1]["close"] if bars else None
            intervals.append(current_interval)

        return intervals

    def walk_extend(self, segment: PriceSegment) -> PriceSegment:
        """Extend a price segment using sub-node walk analysis.

        Looks at sub-nodes of the segment's source interval to determine
        if the segment can be extended in the direction of the trend.
        """
        source = segment.source_interval
        if not source.sub_nodes:
            return segment

        # Find the last sub-node that continues in the same direction
        extension_candidate = None
        for sub in reversed(source.sub_nodes):
            if sub.direction == segment.direction:
                extension_candidate = sub
                break

        if extension_candidate and extension_candidate.end_price:
            extended = PriceSegment(
                direction=segment.direction,
                entry_time=segment.entry_time,
                exit_time=extension_candidate.end_time,
                entry_price=segment.entry_price,
                exit_price=extension_candidate.end_price,
                source_interval=source,
                extended=True,
            )
            return extended

        return segment
