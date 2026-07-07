from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from noviscope.agents.assignments import AgentAssignmentService
from noviscope.agents.registry import AGENT_REGISTRY
from noviscope.api.dependencies import get_session
from noviscope.api.routes import get_provider_service
from noviscope.auth.dependencies import get_current_user
from noviscope.models.provider import ModelProvider, ProviderKind, ProviderScope
from noviscope.models.user import User, UserRole

router = APIRouter()


class AgentAssignmentUpdateRequest(BaseModel):
    provider_id: str | None = None
    model_name: str | None = None


class AgentAssignmentResponse(BaseModel):
    agent_id: str
    display_name: str
    provider_id: str | None
    provider_name: str | None
    provider_kind: ProviderKind | None
    provider_is_active: bool | None
    model_name: str | None
    effective_model: str | None


class AgentAssignmentsResponse(BaseModel):
    assignments: list[AgentAssignmentResponse]


def agent_assignment_response(
    agent_id: str,
    provider: ModelProvider | None,
    model_name: str | None,
) -> AgentAssignmentResponse:
    spec = AGENT_REGISTRY[agent_id]
    return AgentAssignmentResponse(
        agent_id=agent_id,
        display_name=spec.display_name,
        effective_model=model_name or provider.default_model if provider is not None else None,
        model_name=model_name,
        provider_id=provider.id if provider is not None else None,
        provider_is_active=provider.is_active if provider is not None else None,
        provider_kind=provider.kind if provider is not None else None,
        provider_name=provider.name if provider is not None else None,
    )


@router.get("/agent-assignments", response_model=AgentAssignmentsResponse)
def list_agent_assignments(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentAssignmentsResponse:
    assignment_service = AgentAssignmentService(session)
    provider_service = get_provider_service(session)
    providers = {
        provider.id: provider for provider in provider_service.list_providers_for_user(current_user)
    }
    assignments = {
        assignment.agent_id: assignment
        for assignment in assignment_service.list_assignments()
    }
    return AgentAssignmentsResponse(
        assignments=[
            agent_assignment_response(
                agent_id,
                providers.get(assignments[agent_id].provider_id or ""),
                assignments[agent_id].model_name if agent_id in assignments else None,
            )
            if agent_id in assignments
            else agent_assignment_response(agent_id, None, None)
            for agent_id in AGENT_REGISTRY
        ]
    )


@router.put("/agent-assignments/{agent_id}", response_model=AgentAssignmentResponse)
def update_agent_assignment(
    agent_id: str,
    request: AgentAssignmentUpdateRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentAssignmentResponse:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    assignment_service = AgentAssignmentService(session)
    provider_service = get_provider_service(session)
    try:
        if request.provider_id is None:
            assignment = assignment_service.clear_assignment(agent_id)
            return agent_assignment_response(assignment.agent_id, None, assignment.model_name)

        provider = provider_service.get_provider_for_user(request.provider_id, current_user)
        if provider.scope != ProviderScope.SHARED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent defaults must use a shared provider.",
            )
        if not provider.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent defaults must use an active provider.",
            )
        assignment = assignment_service.upsert_assignment(
            agent_id,
            model_name=request.model_name,
            provider_id=provider.id,
        )
        return agent_assignment_response(assignment.agent_id, provider, assignment.model_name)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
