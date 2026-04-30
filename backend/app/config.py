from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-exp"
    database_url: str = "sqlite+aiosqlite:///./data/pipeline.db"
    data_dir: Path = Path("./data")
    log_level: str = "INFO"

    @property
    def structures_dir(self) -> Path:
        return self.data_dir / "structures"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"


settings = Settings()
settings.structures_dir.mkdir(parents=True, exist_ok=True)
settings.reports_dir.mkdir(parents=True, exist_ok=True)
