#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Multi-object tracker for traffic light annotation persistence."""
import numpy as np
import cv2
from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class TrackResult:
    """Result of tracking a single object across frames."""
    track_id: int
    bbox: tuple[int, int, int, int]  # x, y, w, h
    confidence: float
    category: str
    lost_frames: int = 0


@dataclass
class TrackerState:
    """Internal state of the tracker."""
    tracks: list[TrackResult] = field(default_factory=list)
    next_id: int = 0
    frame_count: int = 0


class MultiObjectTracker:
    """Tracks multiple annotated objects across video frames.

    Uses a combination of IoU matching and optional optical flow
    to maintain object identity across frames.
    """

    def __init__(self, iou_threshold: float = 0.3, max_lost: int = 5):
        self.iou_threshold = iou_threshold
        self.max_lost = max_lost
        self.state = TrackerState()
        self._prev_gray: Optional[np.ndarray] = None

    def _compute_iou(self, box1: tuple, box2: tuple) -> float:
        """Compute IoU between two bounding boxes (x, y, w, h format)."""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2

        xi = max(x1, x2)
        yi = max(y1, y2)
        xf = min(x1 + w1, x2 + w2)
        yf = min(y1 + h1, y2 + h2)

        if xf <= xi or yf <= yi:
            return 0.0

        intersection = (xf - xi) * (yf - yi)
        union = w1 * h1 + w2 * h2 - intersection
        return intersection / union if union > 0 else 0.0

    def _match_detections(
        self,
        detections: list[tuple[int, int, int, int]],
        categories: list[str]
    ) -> list[tuple[int, int]]:
        """Match new detections to existing tracks using IoU.

        Returns list of (track_idx, detection_idx) pairs.
        """
        if not self.state.tracks or not detections:
            return []

        # Build IoU matrix
        n_tracks = len(self.state.tracks)
        n_dets = len(detections)
        iou_matrix = np.zeros((n_tracks, n_dets))

        for i, track in enumerate(self.state.tracks):
            for j, det in enumerate(detections):
                # Only match same category
                if track.category == categories[j]:
                    iou_matrix[i, j] = self._compute_iou(track.bbox, det)

        # Greedy matching
        matches = []
        used_tracks = set()
        used_dets = set()

        # Find best matches iteratively
        while True:
            if iou_matrix.size == 0:
                break
            best_idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
            best_iou = iou_matrix[best_idx]

            if best_iou < self.iou_threshold:
                break

            ti, di = best_idx
            if ti not in used_tracks and di not in used_dets:
                matches.append((ti, di))
                used_tracks.add(ti)
                used_dets.add(di)

            iou_matrix[ti, :] = 0
            iou_matrix[:, di] = 0

        return matches

    def update(
        self,
        frame: np.ndarray,
        detections: list[tuple[int, int, int, int]],
        categories: list[str]
    ) -> list[TrackResult]:
        """Update tracker with new frame and detections.

        Args:
            frame: Current video frame (BGR)
            detections: List of (x, y, w, h) bounding boxes
            categories: Category label for each detection

        Returns:
            Updated list of active tracks
        """
        self.state.frame_count += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Match detections to existing tracks
        matches = self._match_detections(detections, categories)
        matched_tracks = {m[0] for m in matches}
        matched_dets = {m[1] for m in matches}

        # Update matched tracks
        for ti, di in matches:
            self.state.tracks[ti].bbox = detections[di]
            self.state.tracks[ti].confidence = 1.0
            self.state.tracks[ti].lost_frames = 0

        # Create new tracks for unmatched detections
        for di in range(len(detections)):
            if di not in matched_dets:
                new_track = TrackResult(
                    track_id=self.state.next_id,
                    bbox=detections[di],
                    confidence=1.0,
                    category=categories[di],
                )
                self.state.tracks.append(new_track)
                self.state.next_id += 1

        # Update lost counts and remove old tracks
        active_tracks = []
        for i, track in enumerate(self.state.tracks):
            if i not in matched_tracks and i < len(self.state.tracks) - len(detections) + len(matched_dets):
                track.lost_frames += 1
                track.confidence *= 0.9

            if track.lost_frames <= self.max_lost:
                active_tracks.append(track)

        self.state.tracks = active_tracks
        self._prev_gray = gray

        return self.state.tracks

    def get_track_summary(self) -> dict:
        """Get summary of all tracks with their status."""
        return {
            'total_tracks': self.state.next_id,
            'active_tracks': len(self.state.tracks),
            'frame_count': self.state.frame_count,
            'tracks': [
                {
                    'id': t.track_id,
                    'bbox': t.bbox,
                    'category': t.category,
                    'confidence': round(t.confidence, 3),
                    'lost': t.lost_frames,
                }
                for t in self.state.tracks
            ]
        }


def interpolate_track_positions(
    tracks_by_frame: dict[int, list[TrackResult]],
    target_frame: int,
    window: int = 3
) -> list[TrackResult]:
    """Interpolate track positions for a target frame using nearby frames.

    Uses linear interpolation from adjacent annotated frames.
    """
    # Find nearest annotated frames before and after target
    frames = sorted(tracks_by_frame.keys())
    before = [f for f in frames if f < target_frame]
    after = [f for f in frames if f > target_frame]

    if not before or not after:
        # Can't interpolate without both sides
        return tracks_by_frame.get(target_frame, [])

    prev_frame = before[-1]
    next_frame = after[0]

    # Filter by window size
    if target_frame - prev_frame > window or next_frame - target_frame > window:
        return []

    alpha = (target_frame - prev_frame) / (next_frame - prev_frame)

    prev_tracks = {t.track_id: t for t in tracks_by_frame[prev_frame]}
    next_tracks = {t.track_id: t for t in tracks_by_frame[next_frame]}

    # Interpolate matching track IDs
    interpolated = []
    for tid in prev_tracks:
        if tid in next_tracks:
            pt = prev_tracks[tid]
            nt = next_tracks[tid]
            # Linear interpolation of bbox
            interp_bbox = tuple(
                int(p * (1 - alpha) + n * alpha)
                for p, n in zip(pt.bbox, nt.bbox, strict=True)
            )
            interpolated.append(TrackResult(
                track_id=tid,
                bbox=interp_bbox,
                confidence=min(pt.confidence, nt.confidence) * 0.8,
                category=pt.category,
            ))

    return interpolated
