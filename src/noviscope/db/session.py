from collections.abc import Generator
from sqlite3 import Connection

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from noviscope.models.agent import AgentAssignment  # noqa: F401
from noviscope.models.provider import ModelProvider  # noqa: F401
from noviscope.models.quest import Quest, StageCard  # noqa: F401


def create_db_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine_kwargs: dict[str, object] = {"connect_args": connect_args}
    if database_url in {"sqlite:///:memory:", "sqlite://"}:
        engine_kwargs["poolclass"] = StaticPool
    engine = create_engine(database_url, **engine_kwargs)
    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection: Connection, _: object) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_schema(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)


def session_generator(engine: Engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
