# -*- coding: utf-8 -*-
"""巡检主流程：检测 -> 深度计算 -> 手眼转换 -> 动作执行。

深度处理策略：
- 若 depth.use_plane_rpy=True 且画面中存在 screen（screen_on/screen_off），
  先拟合屏幕平面，再在平面内计算目标按钮深度 + 法向量姿态。
- 否则直接对 box 中心求深度，保持当前姿态。

注：相机预热已在 RealSenseCamera.initialize() 中完成（丢弃前几帧等曝光稳定），
    此处直接单帧检测即可，无需多帧融合。
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.config_loader import get_config
from src.logger import get_logger

logger = get_logger()


# ===========================================================================
# 图像保存工具函数
# ===========================================================================

def _save_images(
    color: np.ndarray,
    det_img: np.ndarray,
    cfg,
) -> None:
    """保存原始图像和检测结果图像。

    Args:
        color: 原始相机 BGR 图像
        det_img: 绘制了检测框的图像
        cfg: AppConfig 实例
    """
    if not cfg.service.save_image:
        return
    save_dir = cfg.service.image_save_path
    save_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    if cfg.service.save_raw:
        raw_path = save_dir / "raw.jpg"  # 固定文件名
        cv2.imwrite(str(raw_path), color)
        logger.debug(f"已保存原始图像: {raw_path}")
    if cfg.service.save_det:
        det_path = save_dir / "det.jpg"  # 固定文件名
        cv2.imwrite(str(det_path), det_img)
        logger.debug(f"已保存检测图像: {det_path}")


# ===========================================================================
# 检测结果数据类
# ===========================================================================

class DetectionResult:
    """单次检测结果。"""

    def __init__(self, boxes: List[Dict], class_names: List[str]):
        self.boxes = boxes
        self.class_names = class_names

    @property
    def has_targets(self) -> bool:
        return len(self.boxes) > 0

    def get_center(self, idx: int = 0) -> Tuple[int, int]:
        """获取指定检测框中心像素坐标。"""
        if idx >= len(self.boxes):
            return (0, 0)
        box = self.boxes[idx]
        cx = int((box["x1"] + box["x2"]) / 2)
        cy = int((box["y1"] + box["y2"]) / 2)
        return (cx, cy)


# ===========================================================================
# 巡检主流程
# ===========================================================================

class Inspector:
    """巡检控制器：相机采集 -> 检测 -> 手眼转换 -> 机械臂执行。"""

    def __init__(self, config_path: str = "config.yaml"):
        self.cfg = get_config(config_path)
        self._detection_count = 0

    def run_single_inspection(self, color: np.ndarray, depth: np.ndarray) -> Optional[DetectionResult]:
        """执行单次巡检流程。

        Args:
            color: BGR 彩色图像 (H, W, 3)
            depth: 深度图 (H, W) uint16

        Returns:
            DetectionResult 或 None（无目标时）
        """
        logger.info("开始单次巡检...")
        self._detection_count += 1

        # 模拟检测 (实际使用 YOLO)
        det_img = color.copy()
        boxes = self._mock_detect(color)

        if not boxes:
            logger.info("未检测到目标")
            return None

        # 绘制检测框
        for box in boxes:
            cv2.rectangle(
                det_img,
                (box["x1"], box["y1"]),
                (box["x2"], box["y2"]),
                (0, 255, 0),
                2,
            )

        # 保存图像
        _save_images(color, det_img, self.cfg)

        result = DetectionResult(boxes, [b.get("class", "unknown") for b in boxes])
        logger.info(f"检测到 {len(boxes)} 个目标")
        return result

    def _mock_detect(self, img: np.ndarray) -> List[Dict]:
        """模拟目标检测（实际项目中调用 YOLO 推理）。"""
        h, w = img.shape[:2]
        # 返回模拟检测框
        return [
            {"x1": w // 4, "y1": h // 4, "x2": w // 2, "y2": h // 2, "class": "button_1", "conf": 0.92},
        ]


def main():
    """测试入口。"""
    cfg = get_config()
    inspector = Inspector()

    # 模拟图像
    fake_color = np.zeros((480, 640, 3), dtype=np.uint8)
    fake_depth = np.zeros((480, 640), dtype=np.uint16)

    result = inspector.run_single_inspection(fake_color, fake_depth)
    if result and result.has_targets:
        center = result.get_center(0)
        logger.info(f"目标中心: {center}")


if __name__ == "__main__":
    main()
