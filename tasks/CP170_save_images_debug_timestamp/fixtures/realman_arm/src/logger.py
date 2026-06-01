# -*- coding: utf-8 -*-
"""项目日志模块 — 基于 config.yaml 中 logging.level 配置。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

_logger: Optional[logging.Logger] = None


def get_logger(name: str = "realman_arm") -> logging.Logger:
    """获取配置好的 logger 实例。"""
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)  # default, overridden by config_loader
    return _logger
