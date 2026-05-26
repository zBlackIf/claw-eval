"""Video frame extraction and processing"""
import cv2
from typing import List, Optional
from app.config import settings
from app.utils.logger import logger


class VideoProcessor:
    """Extracts frames from video files for cover recommendation"""

    def __init__(self):
        self.max_frames = settings.MAX_FRAMES
        self.skip_frames = settings.SKIP_FRAMES

    def extract_frames(self, video_path: str, reqid: str = "") -> List:
        """
        Extract frames from a local video file.

        Args:
            video_path: Path to the video file on disk
            reqid: Request ID for logging

        Returns:
            List of extracted frames (as numpy arrays)
        """
        frames = []
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Reqid: {reqid} Cannot open video: {video_path}")
            return frames

        frame_count = 0
        extracted = 0
        try:
            while extracted < self.max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_count += 1
                if self.skip_frames > 0 and frame_count % (self.skip_frames + 1) != 1:
                    continue
                frames.append(frame)
                extracted += 1
        finally:
            cap.release()

        logger.info(f"Reqid: {reqid} Extracted {len(frames)} frames from {frame_count} total")
        return frames
