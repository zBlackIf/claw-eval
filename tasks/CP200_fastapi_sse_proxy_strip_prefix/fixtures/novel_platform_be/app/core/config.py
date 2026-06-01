"""Application settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LANGCHAIN_HOST: str = "http://10.200.16.102:8000"
    DATABASE_URL: str = "sqlite:///./test.db"
    MINIO_ENDPOINT: str = "10.200.16.102:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "novels"
    MINIO_SECURE: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
