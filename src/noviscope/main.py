from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from noviscope.api.artifacts import router as artifacts_router
from noviscope.api.dependencies import get_session
from noviscope.api.idea_selection import router as idea_selection_router
from noviscope.api.provider_tests import router as provider_tests_router
from noviscope.api.routes import router
from noviscope.api.stage_literature_papers import router as stage_literature_papers_router
from noviscope.api.stage_readiness import router as stage_readiness_router
from noviscope.api.stage_runs import router as stage_runs_router
from noviscope.api.version_routes import router as version_router
from noviscope.core.config import get_settings, validate_deployment_settings
from noviscope.db.session import create_db_engine, create_schema, session_generator


def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings()
    effective_database_url = database_url or settings.database_url
    validate_deployment_settings(settings, effective_database_url)
    engine = create_db_engine(effective_database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        create_schema(engine)
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)
    app.include_router(artifacts_router)
    app.include_router(idea_selection_router)
    app.include_router(provider_tests_router)
    app.include_router(stage_literature_papers_router)
    app.include_router(stage_readiness_router)
    app.include_router(stage_runs_router)
    app.include_router(version_router)

    def session_dependency() -> Generator[Session, None, None]:
        yield from session_generator(engine)

    app.dependency_overrides[get_session] = session_dependency
    return app


app = create_app()
