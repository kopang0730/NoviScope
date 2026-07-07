from dataclasses import dataclass
from typing import Annotated, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from noviscope.agents.assignments import AgentAssignmentService
from noviscope.agents.stage_runner import ModelProviderCredentials, StageRunnerRegistry
from noviscope.api.dependencies import get_session
from noviscope.api.routes import get_provider_service
from noviscope.api.stage_provider_selection import (
    ProviderSelectionContext,
    build_provider_block,
    build_server_managed_provider,
    select_provider,
)
from noviscope.api.stage_run_blocks import (
    StageBlock,
    build_dependency_block_if_needed,
    build_runner_block,
)
from noviscope.api.stage_runs import (
    get_stage_runner_registry,
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
class StageReadinessBuildRequest:
    stage: StageCard
    workflow_stages: list[StageCard]
    provider_id: str | None


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


def build_stage_status_block(stage: StageCard) -> StageBlock | None:
    match stage.status:
        case StageStatus.COMPLETE:
            return StageBlock(
                evidence_payload={
                    "blocking_detail": "Completed stages are locked until versioned reruns exist.",
                    "blocking_reason": "stage_already_complete",
                },
                summary="Stage is already complete.",
            )
        case StageStatus.RUNNING:
            return StageBlock(
                evidence_payload={
                    "blocking_detail": (
                        "Wait for the current run to finish before starting another run."
                    ),
                    "blocking_reason": "stage_already_running",
                },
                summary="Stage is already running.",
            )
        case StageStatus.PENDING | StageStatus.BLOCKED:
            return None
        case unreachable:
            assert_never(unreachable)


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


def build_stage_readiness_response(
    request: StageReadinessBuildRequest,
    context: StageReadinessRequestContext,
) -> StageReadinessResponse:
    status_block = build_stage_status_block(request.stage)
    if status_block is not None:
        return build_blocked_response(request.stage, status_block)

    runner = context.registry.get_runner(request.stage.agent_id)
    if runner is None:
        return build_blocked_response(request.stage, build_runner_block(request.stage))

    dependency_block = build_dependency_block_if_needed(request.stage, request.workflow_stages)
    if dependency_block is not None:
        return build_blocked_response(request.stage, dependency_block)

    if not runner.supported_provider_kinds:
        return build_ready_response(
            request.stage,
            server_managed_provider(build_server_managed_provider()),
        )

    provider_service = get_provider_service(context.session)
    assignment_service = AgentAssignmentService(context.session)
    assignment = assignment_service.get_assignment(request.stage.agent_id)
    configured_provider_id = assignment.provider_id if assignment is not None else None
    configured_model_name = assignment.model_name if assignment is not None else None
    effective_provider_id = (
        request.provider_id if request.provider_id is not None else configured_provider_id
    )
    effective_model_name = None if request.provider_id is not None else configured_model_name
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
        return build_blocked_response(request.stage, build_provider_block(selection))
    return build_ready_response(
        request.stage,
        selected_model_provider(selection.provider, selection.model_name),
    )


@router.get("/stages/{stage_id}/readiness", response_model=StageReadinessResponse)
def get_stage_readiness(
    stage_id: str,
    context: Annotated[StageReadinessRequestContext, Depends(get_stage_readiness_context)],
    provider_id: str | None = None,
) -> StageReadinessResponse:
    quest_service = QuestService(context.session)
    try:
        stage = quest_service.get_stage_card_for_user(stage_id, context.current_user)
        quest = quest_service.get_quest_for_user(stage.quest_id, context.current_user)
        return build_stage_readiness_response(
            StageReadinessBuildRequest(
                provider_id=provider_id,
                stage=stage,
                workflow_stages=quest_service.list_stage_cards(quest.id),
            ),
            context,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
