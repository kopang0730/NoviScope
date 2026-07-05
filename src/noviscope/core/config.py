from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_PROVIDER_SECRET_KEY = "noviscope-dev-secret-key-change-me"
DEFAULT_SESSION_SECRET_KEY = "noviscope-session-dev-secret-change-me"
PLACEHOLDER_SECRET_PREFIX = "replace-with-"
MIN_SHARED_SECRET_LENGTH = 32
MIN_SHARED_SECRET_UNIQUE_CHARS = 12


class Settings(BaseSettings):
    app_name: str = "NoviScope"
    database_url: str = Field(default="sqlite:///./noviscope.db")
    allow_external_private_uploads: bool = Field(default=False)
    provider_secret_key: str = Field(default=DEFAULT_PROVIDER_SECRET_KEY)
    session_secret_key: str = Field(default=DEFAULT_SESSION_SECRET_KEY)
    session_cookie_name: str = Field(default="noviscope_session")
    session_cookie_secure: bool = Field(default=True)
    dev_admin_header_enabled: bool = Field(default=False)
    dev_admin_token: str | None = Field(default=None)
    artifact_root: str = Field(default=".noviscope/artifacts")
    openalex_email: str | None = Field(default=None)
    openalex_api_key: SecretStr | None = Field(default=None, repr=False)

    model_config = SettingsConfigDict(env_prefix="NOVISCOPE_", env_file=".env")


def is_sqlite_database_url(database_url: str) -> bool:
    return database_url.strip().lower().startswith("sqlite")


def is_placeholder_secret(secret: str) -> bool:
    stripped_secret = secret.strip()
    return stripped_secret in {
        DEFAULT_PROVIDER_SECRET_KEY,
        DEFAULT_SESSION_SECRET_KEY,
    } or stripped_secret.startswith(PLACEHOLDER_SECRET_PREFIX)


def is_strong_shared_secret(secret: str | None) -> bool:
    if secret is None:
        return False
    stripped_secret = secret.strip()
    return (
        len(stripped_secret) >= MIN_SHARED_SECRET_LENGTH
        and len(set(stripped_secret)) >= MIN_SHARED_SECRET_UNIQUE_CHARS
        and not is_placeholder_secret(stripped_secret)
    )


def validate_deployment_settings(
    settings: Settings,
    database_url: str | None = None,
) -> None:
    effective_database_url = database_url or settings.database_url
    if is_sqlite_database_url(effective_database_url):
        return

    weak_env_vars: list[str] = []
    if not is_strong_shared_secret(settings.provider_secret_key):
        weak_env_vars.append("NOVISCOPE_PROVIDER_SECRET_KEY")
    if not is_strong_shared_secret(settings.session_secret_key):
        weak_env_vars.append("NOVISCOPE_SESSION_SECRET_KEY")
    if settings.dev_admin_header_enabled and not is_strong_shared_secret(
        settings.dev_admin_token
    ):
        weak_env_vars.append("NOVISCOPE_DEV_ADMIN_TOKEN")

    if weak_env_vars:
        env_var_list = ", ".join(weak_env_vars)
        raise ValueError(
            "Non-SQLite/shared deployments require non-placeholder, high-entropy "
            f"secrets of at least {MIN_SHARED_SECRET_LENGTH} characters for "
            f"{env_var_list} before startup."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
