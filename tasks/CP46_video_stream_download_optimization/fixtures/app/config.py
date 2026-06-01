import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application configuration"""
    SERVICE_HOST: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Video processing
    MAX_FRAMES: int = int(os.getenv("MAX_FRAMES", "100"))
    SKIP_FRAMES: int = int(os.getenv("SKIP_FRAMES", "0"))
    MAX_VIDEO_SIZE_MB: int = int(os.getenv("MAX_VIDEO_SIZE_MB", "500"))

    # Temp file config
    TEMP_DIR: str = os.getenv("TEMP_DIR", "/tmp/video-cover")
    AUTO_CLEANUP: bool = os.getenv("AUTO_CLEANUP", "true").lower() == "true"

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
