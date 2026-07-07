from dataclasses import dataclass
from typing import Annotated, Final, Literal, TypeAlias, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from noviscope.api.stage_readiness import (
    StageReadinessBuildRequest,
    StageReadinessRequestContext,
    StageReadinessResponse,
    build_stage_readiness_response,
    get_stage_readiness_context,
)
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.models.provider import ProviderKind, ProviderScope
from noviscope.models.quest import StageCard, StageStatus
from noviscope.quests.service import QuestService

router = APIRouter()

AutopilotStatus: TypeAlias = Literal[
    "ready_to_run",
    "waiting_for_human_review",
    "needs_configuration",
    "blocked",
    "complete",
]
AutopilotStepAction: TypeAlias = Literal[
    "run_next",
    "already_complete",
    "await_human_review",
    "needs_configuration",
    "blocked",
]

CONFIGURATION_BLOCKING_REASONS: Final = frozenset(
    {
        "inactive_provider",
        "missing_provider",
        "unsupported_provider",
    }
)
HUMAN_REVIEW_AGENT_IDS: Final = frozenset(
    {
        DEMAND_VALIDATOR_AGENT_ID,
        EXPERIMENT_PLANNER_AGENT_ID,
        IDEA_GENERATOR_AGENT_ID,
        PAPER_MEETING_WRITER_AGENT_ID,
    }
)


class AutopilotStepResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_id: str
    agent_id: str
    title: str
    status: StageStatus
    action: AutopilotStepAction
    can_run: bool
    blocking_reason: str
    blocking_detail: str
    requires_human_review: bool
    human_approved: bool | None
    provider_id: str | None
    provider_name: str | None
    provider_kind: ProviderKind | None
    provider_model: str | None
    provider_scope: ProviderScope | None
    uses_server_managed_provider: bool


class AutopilotPlanResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    quest_id: str
    status: AutopilotStatus
    summary: str
    next_stage_id: str | None
    next_stage_title: str | None
    stop_stage_id: str | None
    stop_stage_title: str | None
    steps: list[AutopilotStepResponse]


@dataclass(frozen=True, slots=True)
class AutopilotDecision:
    status: AutopilotStatus
    summary: str
    next_stage_id: str | None
    next_stage_title: str | None
    stop_stage_id: str | None
    stop_stage_title: str | None


def requires_human_review(stage: StageCard) -> bool:
    return stage.agent_id in HUMAN_REVIEW_AGENT_IDS


def human_review_is_pending(stage: StageCard) -> bool:
    return (
        stage.status == StageStatus.COMPLETE
        and requires_human_review(stage)
        and stage.human_approved is None
    )


def step_action(stage: StageCard, readiness: StageReadinessResponse) -> AutopilotStepAction:
    if human_review_is_pending(stage):
        return "await_human_review"
    if readiness.can_run:
        return "run_next"
    if stage.status == StageStatus.COMPLETE:
        return "already_complete"
    if readiness.blocking_reason in CONFIGURATION_BLOCKING_REASONS:
        return "needs_configuration"
    return "blocked"


def build_step(stage: StageCard, readiness: StageReadinessResponse) -> AutopilotStepResponse:
    return AutopilotStepResponse(
        action=step_action(stage, readiness),
        agent_id=stage.agent_id,
        blocking_detail=readiness.blocking_detail,
        blocking_reason=readiness.blocking_reason,
        can_run=readiness.can_run,
        human_approved=stage.human_approved,
        provider_id=readiness.provider_id,
        provider_kind=readiness.provider_kind,
        provider_model=readiness.provider_model,
        provider_name=readiness.provider_name,
        provider_scope=readiness.provider_scope,
        requires_human_review=requires_human_review(stage),
        stage_id=stage.id,
        status=stage.status,
        title=stage.title,
        uses_server_managed_provider=readiness.uses_server_managed_provider,
    )


def decide_plan(steps: list[AutopilotStepResponse]) -> AutopilotDecision:
    for step in steps:
        match step.action:
            case "already_complete":
                continue
            case "run_next":
                return AutopilotDecision(
                    next_stage_id=step.stage_id,
                    next_stage_title=step.title,
                    status="ready_to_run",
                    stop_stage_id=step.stage_id,
                    stop_stage_title=step.title,
                    summary=f"Autopilot can run {step.title} next.",
                )
            case "await_human_review":
                return AutopilotDecision(
                    next_stage_id=None,
                    next_stage_title=None,
                    status="waiting_for_human_review",
                    stop_stage_id=step.stage_id,
                    stop_stage_title=step.title,
                    summary=f"Autopilot is waiting for human review on {step.title}.",
                )
            case "needs_configuration":
                return AutopilotDecision(
                    next_stage_id=None,
                    next_stage_title=None,
                    status="needs_configuration",
                    stop_stage_id=step.stage_id,
                    stop_stage_title=step.title,
                    summary=f"Autopilot needs configuration before {step.title} can run.",
                )
            case "blocked":
                return AutopilotDecision(
                    next_stage_id=None,
                    next_stage_title=None,
                    status="blocked",
                    stop_stage_id=step.stage_id,
                    stop_stage_title=step.title,
                    summary=f"Autopilot is blocked at {step.title}: {step.blocking_detail}",
                )
            case unreachable:
                assert_never(unreachable)
    return AutopilotDecision(
        next_stage_id=None,
        next_stage_title=None,
        status="complete",
        stop_stage_id=None,
        stop_stage_title=None,
        summary="All workflow stages are complete.",
    )


def build_autopilot_plan(
    quest_id: str,
    stages: list[StageCard],
    context: StageReadinessRequestContext,
) -> AutopilotPlanResponse:
    steps = [
        build_step(
            stage,
            build_stage_readiness_response(
                StageReadinessBuildRequest(
                    provider_id=None,
                    stage=stage,
                    workflow_stages=stages,
                ),
                context,
            ),
        )
        for stage in stages
    ]
    decision = decide_plan(steps)
    return AutopilotPlanResponse(
        next_stage_id=decision.next_stage_id,
        next_stage_title=decision.next_stage_title,
        quest_id=quest_id,
        status=decision.status,
        steps=steps,
        stop_stage_id=decision.stop_stage_id,
        stop_stage_title=decision.stop_stage_title,
        summary=decision.summary,
    )


@router.get("/quests/{quest_id}/autopilot-plan", response_model=AutopilotPlanResponse)
def get_workflow_autopilot_plan(
    quest_id: str,
    context: Annotated[StageReadinessRequestContext, Depends(get_stage_readiness_context)],
) -> AutopilotPlanResponse:
    service = QuestService(context.session)
    try:
        quest = service.get_quest_for_user(quest_id, context.current_user)
        return build_autopilot_plan(
            quest.id,
            service.list_stage_cards(quest.id),
            context,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
