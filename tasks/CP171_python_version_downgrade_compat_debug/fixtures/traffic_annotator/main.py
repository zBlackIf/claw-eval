#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Traffic Light Annotation Tool - Desktop Edition v2.0

PyQt5-based annotation tool for traffic light recognition datasets.
Requires: Python 3.9+, PyQt5, OpenCV, numpy
"""
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from typing import Optional
from functools import cached_property

import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QListWidget, QListWidgetItem,
    QMessageBox, QStatusBar, QMenuBar, QAction, QSlider, QComboBox
)
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont

from config import load_config, AppConfig
from utils.image_ops import batch_resize_images, normalize_path_list


# Color scheme for different annotation categories
COLORS = {
    'pole': QColor(233, 69, 96),
    'lamp_box': QColor(0, 217, 255),
    'bulb': QColor(255, 215, 0),
    'sign': QColor(138, 43, 226),
    'selected': QColor(0, 255, 0),
}

# Try importing optical flow module
try:
    from optical_flow import compute_optical_flow, FlowMethod
    HAS_OPTICAL_FLOW = True
except ImportError as e:
    HAS_OPTICAL_FLOW = False
    print(f"Optical flow unavailable: {e}")

# Try importing tracker
try:
    from tracker import MultiObjectTracker, TrackResult
    HAS_TRACKER = True
except ImportError as e:
    HAS_TRACKER = False
    print(f"Tracker unavailable: {e}")


def get_annotation_category(label: str) -> int | str:
    """Map label string to category ID or name.

    Returns an int category ID if known, or the original string if unknown.
    """
    match label:
        case "pole":
            return 0
        case "lamp_box":
            return 1
        case "bulb":
            return 2
        case "sign":
            return 3
        case _:
            return label


def parse_annotation_entry(raw: str) -> dict[str, int | str | list[float]]:
    """Parse a raw annotation string into structured data.

    Format: "category:x,y,w,h:confidence"
    Example: "pole:100,200,50,80:0.95"
    """
    parts = raw.split(":")
    category = parts[0]
    coords = [float(v) for v in parts[1].split(",")]
    conf = float(parts[2]) if len(parts) > 2 else 1.0
    return {"category": category, "coords": coords, "confidence": conf}


class AnnotationState:
    """Manages the current annotation state for a frame."""

    def __init__(self):
        self.boxes: list[dict] = []
        self.selected_idx: int | None = None
        self.is_drawing: bool = False
        self.draw_start: QPoint | None = None

    def add_box(self, category: int | str, rect: QRect) -> None:
        self.boxes.append({
            'category': category,
            'rect': rect,
            'timestamp': datetime.now().isoformat(),
        })

    def remove_selected(self) -> None:
        if self.selected_idx is not None:
            del self.boxes[self.selected_idx]
            self.selected_idx = None


class FrameSequence:
    """Manages a sequence of video frames for annotation."""

    def __init__(self, frame_dir: Path):
        self.frame_dir = frame_dir
        self.frames: list[Path] = sorted(
            frame_dir.glob("*.png"),
            key=lambda p: int(p.stem) if p.stem.isdigit() else p.stem
        )
        self._cache: dict[int, np.ndarray] = {}

    def get_frame(self, idx: int) -> np.ndarray | None:
        """Load and cache a frame by index."""
        if idx < 0 or idx >= len(self.frames):
            return None
        if idx not in self._cache:
            img = cv2.imread(str(self.frames[idx]))
            if img is not None:
                self._cache[idx] = img
        return self._cache.get(idx)

    def get_frame_range(self, start: int, stop: int) -> list[np.ndarray]:
        """Get a range of frames, skipping any that fail to load."""
        return [
            frame
            for idx in range(start, stop)
            if (frame := self.get_frame(idx)) is not None
        ]

    def __len__(self) -> int:
        return len(self.frames)


class MainWindow(QMainWindow):
    """Main application window for traffic light annotation."""

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.setWindowTitle("Traffic Light Annotator v2.0")
        self.setMinimumSize(1200, 800)

        self.frame_seq: FrameSequence | None = None
        self.current_frame_idx: int = 0
        self.annotation_state = AnnotationState()
        self.annotations: dict[int, list[dict]] = {}
        self._undo_stack: list[tuple[int, list[dict]]] = []

        self._setup_ui()
        self._setup_shortcuts()

    @cached_property
    def _supported_formats(self) -> frozenset[str]:
        """Lazy-loaded set of supported image file extensions."""
        return frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tiff"})

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # Canvas area
        self.canvas_label = QLabel()
        self.canvas_label.setMinimumSize(800, 600)
        self.canvas_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.canvas_label, stretch=3)

        # Side panel
        side_panel = QVBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItems(list(COLORS.keys()))
        side_panel.addWidget(QLabel("Category:"))
        side_panel.addWidget(self.category_combo)

        self.box_list = QListWidget()
        side_panel.addWidget(QLabel("Annotations:"))
        side_panel.addWidget(self.box_list)

        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.valueChanged.connect(self._on_frame_change)
        side_panel.addWidget(QLabel("Frame:"))
        side_panel.addWidget(self.frame_slider)

        layout.addLayout(side_panel, stretch=1)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _setup_shortcuts(self):
        pass

    def _on_frame_change(self, idx: int):
        self.current_frame_idx = idx
        self._render_frame()

    def _render_frame(self):
        if self.frame_seq is None:
            return
        frame = self.frame_seq.get_frame(self.current_frame_idx)
        if frame is None:
            return
        # Convert BGR to RGB for Qt
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.canvas_label.setPixmap(QPixmap.fromImage(qimg))

    def load_sequence(self, directory: str):
        path = Path(directory)
        if not path.exists():
            QMessageBox.warning(self, "Error", f"Directory not found: {directory}")
            return
        self.frame_seq = FrameSequence(path)
        self.frame_slider.setMaximum(len(self.frame_seq) - 1)
        self.current_frame_idx = 0
        self._render_frame()
        self.statusBar().showMessage(f"Loaded {len(self.frame_seq)} frames")

    def save_annotations(self, output_path: str):
        data = {
            'version': '2.0',
            'created': datetime.now().isoformat(),
            'frames': {}
        }
        for idx, boxes in self.annotations.items():
            data['frames'][str(idx)] = boxes

        # Ensure parent directory exists
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def export_statistics(self) -> dict[str, int | float]:
        """Export annotation statistics across all frames."""
        category_counts: dict[str, int] = {}
        for idx, boxes in self.annotations.items():
            for box in boxes:
                cat = box.get('category', 'unknown')
                category_counts[cat] = category_counts.get(cat, 0) + 1

        total = sum(category_counts.values())
        return {
            "total_annotations": total,
            "frames_annotated": len(self.annotations),
            "categories": category_counts,
            "avg_per_frame": total / max(len(self.annotations), 1),
        }


def main():
    config = load_config()
    app = QApplication(sys.argv)
    window = MainWindow(config)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
