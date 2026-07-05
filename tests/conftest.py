from collections.abc import Generator
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel

from noviscope.core.config import get_settings
from noviscope.db.session import create_db_engine
from noviscope.models.agent import AgentAssignment  # noqa: F401
from noviscope.models.provider import ModelProvider  # noqa: F401
from noviscope.models.quest import Quest, StageCard  # noqa: F401
from noviscope.models.user import InviteCode, User  # noqa: F401

TEST_DEV_ADMIN_TOKEN = "test-dev-admin-token-0123456789abcdef"


@pytest.fixture(autouse=True)
def local_http_session_cookies(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("NOVISCOPE_SESSION_COOKIE_SECURE", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def dev_admin_header_enabled(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("NOVISCOPE_DEV_ADMIN_HEADER_ENABLED", "true")
    monkeypatch.setenv("NOVISCOPE_DEV_ADMIN_TOKEN", TEST_DEV_ADMIN_TOKEN)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def test_db_path(tmp_path: Path) -> Path:
    return tmp_path / "noviscope-test.db"


@pytest.fixture()
def test_engine(test_db_path: Path):
    engine = create_db_engine(f"sqlite:///{test_db_path}")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    with Session(test_engine) as session:
        yield session
