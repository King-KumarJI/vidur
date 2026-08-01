"""
VIDUR Core Configuration
Module: Core Configuration
Submodule: Settings
Purpose: Centralized application settings loaded from environment variables.
"""

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration for VIDUR.

    All values are sourced from environment variables (or a .env file in
    local development). No secrets or environment-specific values are
    hard-coded, per Article 38 (Controlled Resource Creation Law) and
    Article 39 (Dependency Law) of the VIDUR Constitution.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application identity ---
    APP_NAME: str = "VIDUR"
    APP_FULL_NAME: str = "Virtual Intelligent Development Understanding & Reasoning"
    APP_VERSION: str = "0.1.0"
    CONSTITUTION_VERSION: str = "1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    # --- API ---
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Security ---
    SECRET_KEY: str = Field(..., description="Application secret key, required in all environments")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- MongoDB (per-project isolated databases, Article 21) ---
    MONGODB_URI: str = Field(..., description="Base MongoDB connection URI")
    MONGODB_DB_PREFIX: str = "vidur_project_"
    MONGODB_CONNECT_TIMEOUT_MS: int = 5000

    # --- ChromaDB (per-project isolated vector collections, Article 21) ---
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8001
    CHROMADB_COLLECTION_PREFIX: str = "vidur_project_"

    # --- Logging ---
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"
    LOG_DIR: str = "logs"

    # --- Project Isolation (Article 21) ---
    DEFAULT_PROJECT_ID_HEADER: str = "X-Project-Id"
    ENFORCE_PROJECT_ISOLATION: bool = True

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if not value or len(value) < 16:
            raise ValueError("SECRET_KEY must be set and at least 16 characters long")
        return value

    @field_validator("MONGODB_URI")
    @classmethod
    def validate_mongodb_uri(cls, value: str) -> str:
        if not value.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("MONGODB_URI must start with mongodb:// or mongodb+srv://")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()


settings = get_settings()
