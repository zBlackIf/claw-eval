"""Video loading service"""
import os
import uuid
import asyncio
import httpx
import tempfile
from typing import Optional, Tuple
from app.config import settings
from app.utils.logger import logger

ERROR_SUCCESS = 0
ERROR_VIDEO_DOWNLOAD_FAILED = 400020
ERROR_GET_DOWNLOAD_LINK_FAILED = 400023
ERROR_VIDEO_LOAD_FAILED = 400024


class VideoLoader:
    """Video loader - downloads full video files from cloud storage"""

    def __init__(self):
        self.temp_dir = settings.TEMP_DIR
        self.auto_cleanup = settings.AUTO_CLEANUP
        os.makedirs(self.temp_dir, exist_ok=True)

    async def load_video(
        self,
        file_id: str,
        aone_id: str,
        organization_id: str,
        reqid: str = ""
    ) -> Tuple[Optional[str], int, str]:
        """
        Load video file from cloud storage.

        Returns:
            (local video path, error_code, error_message)
        """
        logger.info(f"Reqid: {reqid} Starting video load")

        download_url = f"https://storage.example.com/files/{file_id}"
        video_path, error_code, error_msg = await self._download_video(download_url, reqid)
        return video_path, error_code, error_msg

    async def _download_video(self, url: str, reqid: str) -> Tuple[Optional[str], int, str]:
        """Download full video to local disk"""
        try:
            logger.info(f"Reqid: {reqid} Downloading video: {url[:80]}...")

            file_ext = os.path.splitext(url.split('?')[0])[1] or '.mp4'
            temp_filename = f"video_{uuid.uuid4().hex}{file_ext}"
            temp_path = os.path.join(self.temp_dir, temp_filename)

            # BUG: Downloads entire video even though only first MAX_FRAMES frames are needed
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                with open(temp_path, 'wb') as f:
                    f.write(response.content)

            file_size = os.path.getsize(temp_path)
            logger.info(f"Reqid: {reqid} Download complete: {temp_path}, size: {file_size / (1024*1024):.2f}MB")
            return temp_path, ERROR_SUCCESS, ""

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error: {e.response.status_code}"
            logger.error(f"Reqid: {reqid} {error_msg}")
            return None, ERROR_VIDEO_DOWNLOAD_FAILED, "Video download failed"
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(f"Reqid: {reqid} {error_msg}", exc_info=True)
            return None, ERROR_VIDEO_DOWNLOAD_FAILED, "Video download failed"

    def cleanup(self, video_path: str, reqid: str = ""):
        """Clean up temporary files"""
        if self.auto_cleanup and video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
                logger.debug(f"Reqid: {reqid} Cleaned up: {video_path}")
            except Exception as e:
                logger.warning(f"Reqid: {reqid} Cleanup failed: {e}")
