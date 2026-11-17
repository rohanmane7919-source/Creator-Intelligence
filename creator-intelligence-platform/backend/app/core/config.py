from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# backend/app/core/config.py -> parents[2] is the backend folder
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "creator_intel"
    DB_USER: str = "postgres"
    DB_PASSWORD: str  # required: no default, so it can never be hard-coded
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # absolute path: works from the project root, from backend/, or from scripts
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    @property
    def database_url(self) -> URL:
        # URL.create safely handles special characters in the password
        return URL.create(
            "postgresql+psycopg2",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )


settings = Settings()