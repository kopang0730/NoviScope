from collections.abc import Generator
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from noviscope.models.agent import AgentAssignment  # noqa: F401
from noviscope.models.provider import ModelProvider  # noqa: F401
from noviscope.models.quest import Quest, StageCard  # noqa: F401


@pytest.fixture()
def test_db_path(tmp_path: Path) -> Path:
    return tmp_path / "noviscope-test.db"


@pytest.fixture()
def test_engine(test_db_path: Path):
    engine = create_engine(f"sqlite:///{test_db_path}")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    with Session(test_engine) as session:
        yield session
