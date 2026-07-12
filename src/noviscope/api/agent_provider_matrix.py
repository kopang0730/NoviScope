from typing import Annotated, assert_never

from fastapi import APIRouter, Depends
from sqlmodel import Session

from noviscope.agents.assignments import AgentAssignmentService
from noviscope.agents.registry import AGENT_REGISTRY, AgentSpec
from noviscope.agents.stage_runner import StageRunnerRegistry
from noviscope.api.agent_provider_matrix_contract import (
    AgentProviderMatrixEntry,
    AgentProviderMatrixResponse,
    MatrixBuildContext,
)
from noviscope.api.agent_provider_matrix_entries import (
    assignment_provider,
    server_managed_entry,
    supported_provider_kinds,
    unavailable_entry,
)
from noviscope.api.agent_provider_matrix_model_provider import model_provider_entry
from noviscope.api.dependencies import get_session
from noviscope.api.routes import get_provider_service
from noviscope.api.stage_runs import get_stage_runner_registry
from noviscope.api.workflow_capabilities import (
    ProviderRequirement,
    build_agent_capability,
)
from noviscope.auth.dependencies import get_current_user
from noviscope.models.user import User

router = APIRouter()


def build_matrix_entry(
    agent: AgentSpec,
    context: MatrixBuildContext,
) -> AgentProviderMatrixEntry:
    capability = build_agent_capability(agent)
    assignment = context.assignments.get(agent.agent_id)
    assigned_provider = assignment_provider(assignment, context.providers_by_id)
    runner = context.registry.get_runner(agent.agent_id)
    supported_kinds = supported_provider_kinds(runner)
    model_name = assignment.model_name if assignment is not None else None

    match capability.provider_requirement:
        case ProviderRequirement.NOT_IMPLEMENTED:
            return unavailable_entry(
                agent=agent,
                assigned_provider=assigned_provider,
                automation_status=capability.automation_status,
                available_provider_count=0,
                model_name=model_name,
                provider_requirement=ProviderRequirement.NOT_IMPLEMENTED,
                reason="stage_runner_not_implemented",
                stage_runner_available=False,
                status_detail=capability.status_detail,
                supported_kinds=supported_kinds,
            )
        case ProviderRequirement.SERVER_MANAGED:
            return server_managed_entry(
                agent,
                capability.automation_status,
                assignment,
                assigned_provider,
            )
        case ProviderRequirement.MODEL_PROVIDER:
            return model_provider_entry(
                agent,
                capability.automation_status,
                assignment,
                assigned_provider,
                context.providers,
                runner,
            )
        case unreachable:
            assert_never(unreachable)


def build_agent_provider_matrix(
    *,
    current_user: User,
    registry: StageRunnerRegistry,
    session: Session,
) -> AgentProviderMatrixResponse:
    provider_service = get_provider_service(session)
    providers = provider_service.list_providers_for_user(current_user)
    assignments = {
        assignment.agent_id: assignment
        for assignment in AgentAssignmentService(session).list_assignments()
    }
    context = MatrixBuildContext(
        assignments=assignments,
        providers=providers,
        providers_by_id={provider.id: provider for provider in providers},
        registry=registry,
    )
    agents = tuple(build_matrix_entry(agent, context) for agent in AGENT_REGISTRY.values())
    runnable_count = sum(entry.can_run_with_current_config for entry in agents)
    return AgentProviderMatrixResponse(
        agents=agents,
        blocked_count=len(agents) - runnable_count,
        runnable_count=runnable_count,
        total_count=len(agents),
    )


@router.get("/agent-provider-matrix", response_model=AgentProviderMatrixResponse)
def get_agent_provider_matrix(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    registry: Annotated[StageRunnerRegistry, Depends(get_stage_runner_registry)],
) -> AgentProviderMatrixResponse:
    return build_agent_provider_matrix(
        current_user=current_user,
        registry=registry,
        session=session,
    )
