from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///../data/disasterinsight.db"
    allowed_origins: str = "http://localhost:5173"
    max_upload_mb: int = 20

    @property
    def origins(self) -> list:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
