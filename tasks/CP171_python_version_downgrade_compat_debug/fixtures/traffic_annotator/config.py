#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Application configuration loader.

Loads settings from TOML config file using Python 3.11+ tomllib.
"""
import tomllib
from pathlib import Path
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class AppConfig:
    """Application configuration."""
    window_title: str = "Traffic Light Annotator"
    window_width: int = 1200
    window_height: int = 800
    auto_save: bool = True
    auto_save_interval: int = 60
    recent_dirs: list[str] = field(default_factory=list)
    default_category: str = "lamp_box"
    flow_method: str = "farneback"
    tracker_iou_threshold: float = 0.3
    tracker_max_lost: int = 5


DEFAULT_CONFIG = """
[window]
title = "Traffic Light Annotator"
width = 1200
height = 800

[behavior]
auto_save = true
auto_save_interval = 60
default_category = "lamp_box"

[tracker]
iou_threshold = 0.3
max_lost_frames = 5

[optical_flow]
method = "farneback"
"""


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load application config from TOML file.

    Args:
        config_path: Path to config file. If None, uses default config.

    Returns:
        Parsed AppConfig instance.
    """
    if config_path is None:
        # Use default config
        data = tomllib.loads(DEFAULT_CONFIG)
    else:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

    window = data.get("window", {})
    behavior = data.get("behavior", {})
    tracker = data.get("tracker", {})
    flow = data.get("optical_flow", {})

    return AppConfig(
        window_title=window.get("title", "Traffic Light Annotator"),
        window_width=window.get("width", 1200),
        window_height=window.get("height", 800),
        auto_save=behavior.get("auto_save", True),
        auto_save_interval=behavior.get("auto_save_interval", 60),
        default_category=behavior.get("default_category", "lamp_box"),
        flow_method=flow.get("method", "farneback"),
        tracker_iou_threshold=tracker.get("iou_threshold", 0.3),
        tracker_max_lost=tracker.get("max_lost_frames", 5),
    )
