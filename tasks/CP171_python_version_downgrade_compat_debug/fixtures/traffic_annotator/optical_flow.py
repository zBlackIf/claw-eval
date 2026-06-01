#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optical flow computation module for frame-to-frame motion estimation."""
import numpy as np
import cv2
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias
import importlib.resources


# Type alias using 3.10+ syntax
FlowArray: TypeAlias = np.ndarray


class FlowMethod(Enum):
    FARNEBACK = "farneback"
    LUCAS_KANADE = "lucas_kanade"
    RAFT = "raft"


@dataclass
class FlowResult:
    """Result of optical flow computation."""
    flow: FlowArray
    magnitude: FlowArray
    angle: FlowArray
    method: FlowMethod


def _load_model_config() -> dict:
    """Load RAFT model configuration from package resources."""
    # Use importlib.resources.files() to locate bundled config
    config_dir = importlib.resources.files("optical_flow_models").joinpath("configs")
    config_path = config_dir / "raft_config.json"
    import json
    with importlib.resources.as_file(config_path) as p:
        return json.loads(p.read_text())


def compute_farneback_flow(prev_gray: np.ndarray, curr_gray: np.ndarray) -> np.ndarray:
    """Compute dense optical flow using Farneback method."""
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0
    )
    return flow


def compute_lucas_kanade_flow(
    prev_gray: np.ndarray,
    curr_gray: np.ndarray,
    points: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Compute sparse optical flow using Lucas-Kanade method.

    Returns (new_points, status) tuple.
    """
    lk_params = dict(
        winSize=(15, 15),
        maxLevel=2,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
    )
    new_points, status, _ = cv2.calcOpticalFlowPyrLK(
        prev_gray, curr_gray, points, None, **lk_params
    )
    return new_points, status


def compute_optical_flow(
    prev_frame: np.ndarray,
    curr_frame: np.ndarray,
    method: FlowMethod = FlowMethod.FARNEBACK,
    points: np.ndarray | None = None,
) -> FlowResult:
    """Compute optical flow between two frames.

    Args:
        prev_frame: Previous frame (BGR)
        curr_frame: Current frame (BGR)
        method: Flow computation method
        points: Optional feature points for sparse methods

    Returns:
        FlowResult with computed flow data
    """
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)

    match method:
        case FlowMethod.FARNEBACK:
            flow = compute_farneback_flow(prev_gray, curr_gray)
        case FlowMethod.LUCAS_KANADE:
            if points is None:
                # Detect good features to track
                points = cv2.goodFeaturesToTrack(
                    prev_gray, maxCorners=200, qualityLevel=0.01,
                    minDistance=10
                )
            new_pts, status = compute_lucas_kanade_flow(prev_gray, curr_gray, points)
            # Create a pseudo-dense flow from sparse points
            flow = np.zeros((*prev_gray.shape, 2), dtype=np.float32)
            for i, (old, new) in enumerate(zip(points, new_pts)):
                if status[i]:
                    ox, oy = old.ravel()
                    nx, ny = new.ravel()
                    y, x = int(oy), int(ox)
                    if 0 <= y < flow.shape[0] and 0 <= x < flow.shape[1]:
                        flow[y, x] = [nx - ox, ny - oy]
        case FlowMethod.RAFT:
            # RAFT requires model - try to load config
            try:
                config = _load_model_config()
                # Placeholder: would use deep learning model
                flow = compute_farneback_flow(prev_gray, curr_gray)
            except Exception:
                flow = compute_farneback_flow(prev_gray, curr_gray)
        case _:
            raise ValueError(f"Unknown method: {method}")

    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    return FlowResult(flow=flow, magnitude=magnitude, angle=angle, method=method)


def get_bbox_displacement(
    flow: np.ndarray,
    bbox: tuple[int, int, int, int]
) -> tuple[float, float]:
    """Get average displacement for a bounding box region.

    Args:
        flow: Dense optical flow array (H, W, 2)
        bbox: (x, y, w, h) bounding box

    Returns:
        (dx, dy) average displacement
    """
    x, y, w, h = bbox
    region = flow[y:y+h, x:x+w]
    if region.size == 0:
        return (0.0, 0.0)
    dx = float(np.mean(region[..., 0]))
    dy = float(np.mean(region[..., 1]))
    return (dx, dy)
