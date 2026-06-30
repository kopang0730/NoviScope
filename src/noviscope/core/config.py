from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NoviScope"
    database_url: str = Field(default="sqlite:///./noviscope.db")
    allow_external_private_uploads: bool = Field(default=False)
    provider_secret_key: str = Field(default="noviscope-dev-secret-key-change-me")

    model_config = SettingsConfigDict(env_prefix="NOVISCOPE_", env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
