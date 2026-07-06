from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from noviscope.agents.assignments import AgentAssignmentService
from noviscope.agents.stage_runner import ModelProviderCredentials, StageRunnerRegistry
from noviscope.api.dependencies import get_session
from noviscope.api.routes import get_provider_service
from noviscope.api.stage_runs import (
    ProviderSelectionContext,
    StageBlock,
    build_dependency_block_if_needed,
    build_provider_block,
    build_runner_block,
    build_server_managed_provider,
    get_stage_runner_registry,
    select_provider,
)
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.models.provider import ModelProvider, ProviderKind, ProviderScope
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()


@dataclass(frozen=True, slots=True)
class StageReadinessRequestContext:
    session: Session
    current_user: User
    registry: StageRunnerRegistry


@dataclass(frozen=True, slots=True)
class ReadinessProvider:
    provider_id: str | None
    provider_name: str | None
    provider_kind: ProviderKind | None
    provider_model: str | None
    provider_scope: ProviderScope | None
    uses_server_managed_provider: bool


class StageReadinessResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_id: str
    quest_id: str
    agent_id: str
    status: StageStatus
    can_run: bool
    summary: str
    blocking_reason: str
    blocking_detail: str
    provider_id: str | None
    provider_name: str | None
    provider_kind: ProviderKind | None
    provider_model: str | None
    provider_scope: ProviderScope | None
    uses_server_managed_provider: bool


def get_stage_readiness_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    registry: Annotated[StageRunnerRegistry, Depends(get_stage_runner_registry)],
) -> StageReadinessRequestContext:
    return StageReadinessRequestContext(
        current_user=current_user,
        registry=registry,
        session=session,
    )


def build_blocked_response(stage: StageCard, block: StageBlock) -> StageReadinessResponse:
    return StageReadinessResponse(
        agent_id=stage.agent_id,
        blocking_detail=string_field(block.evidence_payload, "blocking_detail"),
        blocking_reason=string_field(block.evidence_payload, "blocking_reason"),
        can_run=False,
        provider_id=None,
        provider_kind=None,
        provider_model=None,
        provider_name=None,
        provider_scope=None,
        quest_id=stage.quest_id,
        stage_id=stage.id,
        status=stage.status,
        summary=block.summary,
        uses_server_managed_provider=False,
    )


def build_ready_response(
    stage: StageCard,
    provider: ReadinessProvider,
) -> StageReadinessResponse:
    return StageReadinessResponse(
        agent_id=stage.agent_id,
        blocking_detail="",
        blocking_reason="",
        can_run=True,
        provider_id=provider.provider_id,
        provider_kind=provider.provider_kind,
        provider_model=provider.provider_model,
        provider_name=provider.provider_name,
        provider_scope=provider.provider_scope,
        quest_id=stage.quest_id,
        stage_id=stage.id,
        status=stage.status,
        summary="Stage is ready to run.",
        uses_server_managed_provider=provider.uses_server_managed_provider,
    )


def selected_model_provider(
    provider: ModelProvider,
    model_name: str | None,
) -> ReadinessProvider:
    return ReadinessProvider(
        provider_id=provider.id,
        provider_kind=provider.kind,
        provider_model=model_name or provider.default_model,
        provider_name=provider.name,
        provider_scope=provider.scope,
        uses_server_managed_provider=False,
    )


def server_managed_provider(provider: ModelProviderCredentials) -> ReadinessProvider:
    return ReadinessProvider(
        provider_id=provider.id,
        provider_kind=provider.kind,
        provider_model=provider.model,
        provider_name=provider.name,
        provider_scope=None,
        uses_server_managed_provider=True,
    )


def string_field(payload: JsonObject, key: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) else ""


@router.get("/stages/{stage_id}/readiness", response_model=StageReadinessResponse)
def get_stage_readiness(
    stage_id: str,
    context: Annotated[StageReadinessRequestContext, Depends(get_stage_readiness_context)],
    provider_id: str | None = None,
) -> StageReadinessResponse:
    quest_service = QuestService(context.session)
    provider_service = get_provider_service(context.session)
    assignment_service = AgentAssignmentService(context.session)
    try:
        stage = quest_service.get_stage_card_for_user(stage_id, context.current_user)
        runner = context.registry.get_runner(stage.agent_id)
        if runner is None:
            return build_blocked_response(stage, build_runner_block(stage))

        quest = quest_service.get_quest_for_user(stage.quest_id, context.current_user)
        workflow_stages = quest_service.list_stage_cards(quest.id)
        dependency_block = build_dependency_block_if_needed(stage, workflow_stages)
        if dependency_block is not None:
            return build_blocked_response(stage, dependency_block)

        if not runner.supported_provider_kinds:
            return build_ready_response(
                stage,
                server_managed_provider(build_server_managed_provider()),
            )

        assignment = assignment_service.get_assignment(stage.agent_id)
        configured_provider_id = assignment.provider_id if assignment is not None else None
        configured_model_name = assignment.model_name if assignment is not None else None
        effective_provider_id = provider_id if provider_id is not None else configured_provider_id
        effective_model_name = None if provider_id is not None else configured_model_name
        selection = select_provider(
            ProviderSelectionContext(
                current_user=context.current_user,
                model_name=effective_model_name,
                provider_id=effective_provider_id,
                provider_service=provider_service,
                runner=runner,
            )
        )
        if selection.provider is None:
            return build_blocked_response(stage, build_provider_block(selection))
        return build_ready_response(
            stage,
            selected_model_provider(selection.provider, selection.model_name),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
