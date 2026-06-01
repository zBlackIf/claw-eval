# -*- coding: utf-8 -*-
"""配置加载器 — 从 config.yaml 读取配置并初始化 logger level。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml

from src.logger import get_logger


@dataclass
class ServiceConfig:
    save_image: bool = True
    save_raw: bool = True
    save_det: bool = True
    image_save_path: Path = field(default_factory=lambda: Path("images"))


@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_file: str = "logs/app.log"


@dataclass
class AppConfig:
    service: ServiceConfig = field(default_factory=ServiceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def get_config(config_path: str = "config.yaml") -> AppConfig:
    """读取配置文件并返回 AppConfig 实例。"""
    cfg = AppConfig()
    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        # logging
        log_raw = raw.get("logging", {})
        cfg.logging.level = log_raw.get("level", "INFO").upper()
        cfg.logging.log_file = log_raw.get("log_file", "logs/app.log")

        # 设置 logger 级别
        logger = get_logger()
        logger.setLevel(getattr(logging, cfg.logging.level, logging.INFO))

        # service
        svc_raw = raw.get("service", {})
        cfg.service.save_image = svc_raw.get("save_image", True)
        cfg.service.save_raw = svc_raw.get("save_raw", True)
        cfg.service.save_det = svc_raw.get("save_det", True)
        cfg.service.image_save_path = Path(svc_raw.get("image_save_path", "images"))

    return cfg
