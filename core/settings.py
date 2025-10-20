import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Setting(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    ENV: str = "development"
    REPOSITORIES_STORAGE: str

    DATABASE_DRIVERNAME: str = "postgresql+psycopg2"
    DATABASE_USERNAME: str
    DATABASE_PASSWORD: str
    DATABASE_HOST: str
    DATABASE_PORT: str
    DATABASE_DATABASE: str

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername=setting.DATABASE_DRIVERNAME,
            username=setting.DATABASE_USERNAME,
            password=setting.DATABASE_PASSWORD,
            host=setting.DATABASE_HOST,
            port=setting.DATABASE_PORT,
            database=setting.DATABASE_DATABASE,
        )


setting = Setting()
