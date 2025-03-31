"""Application configuration with environment variable support."""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_QUEUE_NAME: str = "text_generation"
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    
    # Job processing settings
    BATCH_WINDOW_MS: int = 250
    MAX_REQUESTS_PER_JOB: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Create global settings instance
settings = Settings()
