from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_PROVIDER_SECRET_KEY = "noviscope-dev-secret-key-change-me"
DEFAULT_SESSION_SECRET_KEY = "noviscope-session-dev-secret-change-me"
PLACEHOLDER_SECRET_PREFIX = "replace-with-"


class Settings(BaseSettings):
    app_name: str = "NoviScope"
    database_url: str = Field(default="sqlite:///./noviscope.db")
    allow_external_private_uploads: bool = Field(default=False)
    provider_secret_key: str = Field(default=DEFAULT_PROVIDER_SECRET_KEY)
    session_secret_key: str = Field(default=DEFAULT_SESSION_SECRET_KEY)
    session_cookie_name: str = Field(default="noviscope_session")
    session_cookie_secure: bool = Field(default=True)
    dev_admin_header_enabled: bool = Field(default=False)
    artifact_root: str = Field(default=".noviscope/artifacts")

    model_config = SettingsConfigDict(env_prefix="NOVISCOPE_", env_file=".env")


def is_sqlite_database_url(database_url: str) -> bool:
    return database_url.strip().lower().startswith("sqlite")


def is_placeholder_secret(secret: str) -> bool:
    stripped_secret = secret.strip()
    return stripped_secret in {
        DEFAULT_PROVIDER_SECRET_KEY,
        DEFAULT_SESSION_SECRET_KEY,
    } or stripped_secret.startswith(PLACEHOLDER_SECRET_PREFIX)


def validate_deployment_settings(
    settings: Settings,
    database_url: str | None = None,
) -> None:
    effective_database_url = database_url or settings.database_url
    if is_sqlite_database_url(effective_database_url):
        return

    placeholder_env_vars: list[str] = []
    if is_placeholder_secret(settings.provider_secret_key):
        placeholder_env_vars.append("NOVISCOPE_PROVIDER_SECRET_KEY")
    if is_placeholder_secret(settings.session_secret_key):
        placeholder_env_vars.append("NOVISCOPE_SESSION_SECRET_KEY")

    if placeholder_env_vars:
        env_var_list = ", ".join(placeholder_env_vars)
        raise ValueError(
            "Non-SQLite/shared deployments require non-placeholder secrets for "
            f"{env_var_list} before startup."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
