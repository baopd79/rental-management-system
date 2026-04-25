# # app/core/config.py
# Một class chứa tất cả settings mà app cần để chạy: DB URL, JWT secret, environment name, CORS origins, log level...
# Settings được load từ environment variables (không hard-code vào code).
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # === Application ===
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = False

    # === Database ===
    database_url: str  # Required

    # === JWT (ADR-0007) ===
    jwt_secret_key: str  # Required
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # === CORS ===
    cors_origins: list[str] = ["http://localhost:5173"]

    # === Logging ===
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def uppercase_log_level(cls, v: str) -> str:
        v = v.upper()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v not in valid:
            raise ValueError(f"log_level must be one of {valid}, got '{v}'")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
