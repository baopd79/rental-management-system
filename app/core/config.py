from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"

    # Postgres — matches alembic/env.py + docker-compose.yml convention
    postgres_user: str
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str
    postgres_test_db: str = "rms_test"

    # Auth (Stage 1.2+)
    secret_key: str = "changeme"
    access_token_expire_minutes: int = 60

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def test_database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_test_db}"
        )


settings = Settings()
