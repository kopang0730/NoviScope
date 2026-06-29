from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from noviscope.api.routes import get_session, router
from noviscope.core.config import get_settings
from noviscope.db.session import create_db_engine, create_schema, session_generator


def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings()
    engine = create_db_engine(database_url or settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        create_schema(engine)
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)

    def session_dependency() -> Generator[Session, None, None]:
        yield from session_generator(engine)

    app.dependency_overrides[get_session] = session_dependency
    return app


app = create_app()
