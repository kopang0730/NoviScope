from collections.abc import Sequence
from typing import Annotated, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from noviscope.agents.assignments import AgentAssignmentService
from noviscope.agents.stage_runner import StageRunnerRegistry
from noviscope.api.dependencies import get_session
from noviscope.api.provider_setup_guidance_contracts import (
    INACTIVE_PROVIDER_ACTIONS,
    MISSING_ASSIGNED_PROVIDER_ACTIONS,
    MISSING_PROVIDER_ACTIONS,
    RUNNER_MISSING_ACTIONS,
    UNSUPPORTED_PROVIDER_ACTIONS,
    ProviderGuidanceContext,
    ProviderGuidanceDeps,
    ProviderSetupGuidanceResponse,
    ProviderSetupReason,
    ProviderSetupSource,
    ProviderSetupStatus,
    ProviderUsage,
    StageGuidanceSubject,
)
from noviscope.api.routes import get_provider_service
from noviscope.api.stage_runs import (
    build_server_managed_provider,
    get_stage_runner_registry,
)
from noviscope.auth.dependencies import get_current_user
from noviscope.models.agent import AgentAssignment
from noviscope.models.provider import ModelProvider
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()


def get_provider_guidance_deps(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    registry: Annotated[StageRunnerRegistry, Depends(get_stage_runner_registry)],
) -> ProviderGuidanceDeps:
    return ProviderGuidanceDeps(
        current_user=current_user,
        registry=registry,
        session=session,
    )


def build_blocked_guidance(
    stage: StageGuidanceSubject,
    reason: ProviderSetupReason,
    setup_actions: Sequence[str],
) -> ProviderSetupGuidanceResponse:
    return ProviderSetupGuidanceResponse(
        agent_id=stage.agent_id,
        can_run=False,
        provider_status=ProviderSetupStatus.BLOCKED,
        reason=reason,
        setup_actions=list(setup_actions),
        stage_id=stage.stage_id,
    )


def build_server_guidance(context: ProviderGuidanceContext) -> ProviderSetupGuidanceResponse:
    provider = build_server_managed_provider()
    return ProviderSetupGuidanceResponse(
        agent_id=context.stage.agent_id,
        can_run=True,
        provider_id=provider.id,
        provider_kind=provider.kind,
        provider_model=provider.model,
        provider_name=provider.name,
        provider_source=ProviderSetupSource.SERVER_MANAGED,
        provider_status=ProviderSetupStatus.SERVER_MANAGED,
        reason=ProviderSetupReason.SERVER_MANAGED,
        setup_actions=[],
        stage_id=context.stage.stage_id,
        uses_server_managed_provider=True,
    )


def build_ready_guidance(
    context: ProviderGuidanceContext,
    provider: ModelProvider,
    usage: ProviderUsage,
) -> ProviderSetupGuidanceResponse:
    match usage.source:
        case ProviderSetupSource.AGENT_DEFAULT:
            reason = ProviderSetupReason.AGENT_DEFAULT_READY
        case ProviderSetupSource.AUTO_SELECT:
            reason = ProviderSetupReason.AUTO_SELECT_READY
        case ProviderSetupSource.SERVER_MANAGED:
            reason = ProviderSetupReason.SERVER_MANAGED
        case unreachable:
            assert_never(unreachable)

    return ProviderSetupGuidanceResponse(
        agent_id=context.stage.agent_id,
        can_run=True,
        provider_id=provider.id,
        provider_kind=provider.kind,
        provider_model=usage.model_name or provider.default_model,
        provider_name=provider.name,
        provider_scope=provider.scope,
        provider_source=usage.source,
        provider_status=ProviderSetupStatus.READY,
        reason=reason,
        setup_actions=[],
        stage_id=context.stage.stage_id,
    )


def build_assigned_provider_guidance(
    context: ProviderGuidanceContext,
    assignment: AgentAssignment,
) -> ProviderSetupGuidanceResponse:
    if assignment.provider_id is None:
        return build_blocked_guidance(
            context.stage,
            ProviderSetupReason.MISSING_PROVIDER,
            MISSING_PROVIDER_ACTIONS,
        )

    try:
        provider = context.provider_service.get_provider_for_user(
            assignment.provider_id,
            context.current_user,
        )
    except (LookupError, PermissionError):
        return ProviderSetupGuidanceResponse(
            agent_id=context.stage.agent_id,
            can_run=False,
            provider_id=assignment.provider_id,
            provider_source=ProviderSetupSource.AGENT_DEFAULT,
            provider_status=ProviderSetupStatus.BLOCKED,
            reason=ProviderSetupReason.ASSIGNED_PROVIDER_MISSING,
            setup_actions=list(MISSING_ASSIGNED_PROVIDER_ACTIONS),
            stage_id=context.stage.stage_id,
        )

    if not provider.is_active:
        return ProviderSetupGuidanceResponse(
            agent_id=context.stage.agent_id,
            can_run=False,
            provider_id=provider.id,
            provider_kind=provider.kind,
            provider_model=assignment.model_name or provider.default_model,
            provider_name=provider.name,
            provider_scope=provider.scope,
            provider_source=ProviderSetupSource.AGENT_DEFAULT,
            provider_status=ProviderSetupStatus.BLOCKED,
            reason=ProviderSetupReason.ASSIGNED_PROVIDER_INACTIVE,
            setup_actions=list(INACTIVE_PROVIDER_ACTIONS),
            stage_id=context.stage.stage_id,
        )

    if provider.kind not in context.runner.supported_provider_kinds:
        return ProviderSetupGuidanceResponse(
            agent_id=context.stage.agent_id,
            can_run=False,
            provider_id=provider.id,
            provider_kind=provider.kind,
            provider_model=assignment.model_name or provider.default_model,
            provider_name=provider.name,
            provider_scope=provider.scope,
            provider_source=ProviderSetupSource.AGENT_DEFAULT,
            provider_status=ProviderSetupStatus.BLOCKED,
            reason=ProviderSetupReason.ASSIGNED_PROVIDER_UNSUPPORTED,
            setup_actions=list(UNSUPPORTED_PROVIDER_ACTIONS),
            stage_id=context.stage.stage_id,
        )

    return build_ready_guidance(
        context,
        provider,
        ProviderUsage(
            model_name=assignment.model_name,
            source=ProviderSetupSource.AGENT_DEFAULT,
        ),
    )


def build_auto_select_guidance(context: ProviderGuidanceContext) -> ProviderSetupGuidanceResponse:
    for provider in context.provider_service.list_providers_for_user(context.current_user):
        if provider.is_active and provider.kind in context.runner.supported_provider_kinds:
            return build_ready_guidance(
                context,
                provider,
                ProviderUsage(
                    model_name=None,
                    source=ProviderSetupSource.AUTO_SELECT,
                ),
            )

    return build_blocked_guidance(
        context.stage,
        ProviderSetupReason.MISSING_PROVIDER,
        MISSING_PROVIDER_ACTIONS,
    )


@router.get(
    "/stages/{stage_id}/provider-setup-guidance",
    response_model=ProviderSetupGuidanceResponse,
)
def get_provider_setup_guidance(
    stage_id: str,
    deps: Annotated[ProviderGuidanceDeps, Depends(get_provider_guidance_deps)],
) -> ProviderSetupGuidanceResponse:
    quest_service = QuestService(deps.session)
    provider_service = get_provider_service(deps.session)
    assignment_service = AgentAssignmentService(deps.session)

    try:
        stage = quest_service.get_stage_card_for_user(stage_id, deps.current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    runner = deps.registry.get_runner(stage.agent_id)
    stage_subject = StageGuidanceSubject(agent_id=stage.agent_id, stage_id=stage.id)
    if runner is None:
        return build_blocked_guidance(
            stage_subject,
            ProviderSetupReason.RUNNER_NOT_IMPLEMENTED,
            RUNNER_MISSING_ACTIONS,
        )

    context = ProviderGuidanceContext(
        current_user=deps.current_user,
        provider_service=provider_service,
        runner=runner,
        stage=stage_subject,
    )

    if not runner.supported_provider_kinds:
        return build_server_guidance(context)

    assignment = assignment_service.get_assignment(stage.agent_id)
    if assignment is not None and assignment.provider_id is not None:
        return build_assigned_provider_guidance(context, assignment)

    return build_auto_select_guidance(context)
