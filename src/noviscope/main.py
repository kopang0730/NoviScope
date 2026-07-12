from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from noviscope.api.agent_provider_matrix import router as agent_provider_matrix_router
from noviscope.api.artifacts import router as artifacts_router
from noviscope.api.auth_session import router as auth_session_router
from noviscope.api.demand_review import router as demand_review_router
from noviscope.api.dependencies import get_session
from noviscope.api.evidence_ledger import router as evidence_ledger_router
from noviscope.api.experiment_setup import router as experiment_setup_router
from noviscope.api.idea_selection import router as idea_selection_router
from noviscope.api.provider_tests import router as provider_tests_router
from noviscope.api.quest_exports import router as quest_exports_router
from noviscope.api.quest_review_packets import router as quest_review_packets_router
from noviscope.api.routes import router
from noviscope.api.stage_display_output import router as stage_display_output_router
from noviscope.api.stage_literature_papers import router as stage_literature_papers_router
from noviscope.api.stage_readiness import router as stage_readiness_router
from noviscope.api.stage_review_guidance import router as stage_review_guidance_router
from noviscope.api.stage_runs import router as stage_runs_router
from noviscope.api.version_routes import router as version_router
from noviscope.api.workflow_canvas import router as workflow_canvas_router
from noviscope.api.workflow_capabilities import router as workflow_capabilities_router
from noviscope.api.workflow_graph import router as workflow_graph_router
from noviscope.api.workflow_next_actions import router as workflow_next_actions_router
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
    app.include_router(agent_provider_matrix_router)
    app.include_router(artifacts_router)
    app.include_router(auth_session_router)
    app.include_router(demand_review_router)
    app.include_router(evidence_ledger_router)
    app.include_router(experiment_setup_router)
    app.include_router(idea_selection_router)
    app.include_router(provider_tests_router)
    app.include_router(quest_exports_router)
    app.include_router(quest_review_packets_router)
    app.include_router(stage_display_output_router)
    app.include_router(stage_literature_papers_router)
    app.include_router(stage_readiness_router)
    app.include_router(stage_review_guidance_router)
    app.include_router(stage_runs_router)
    app.include_router(version_router)
    app.include_router(workflow_canvas_router)
    app.include_router(workflow_capabilities_router)
    app.include_router(workflow_graph_router)
    app.include_router(workflow_next_actions_router)

    def session_dependency() -> Generator[Session, None, None]:
        yield from session_generator(engine)

    app.dependency_overrides[get_session] = session_dependency
    return app


app = create_app()
