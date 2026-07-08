from typing import Annotated, Final, Literal, TypeAlias, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from noviscope.api.stage_readiness import (
    StageReadinessRequestContext,
    get_stage_readiness_context,
)
from noviscope.api.workflow_graph import (
    GateStatus,
    WorkflowGraphResponse,
    WorkflowNodeResponse,
    build_workflow_graph,
)
from noviscope.models.quest import StageCard, StageStatus
from noviscope.quests.service import QuestService

router = APIRouter()

WorkflowActionType: TypeAlias = Literal[
    "configure_provider",
    "resolve_blocker",
    "review_stage",
    "run_stage",
    "wait_for_stage",
]
BlockingActionType: TypeAlias = Literal["configure_provider", "resolve_blocker"]
COMPLETED_STAGE_BLOCKING_REASON: Final = "stage_already_complete"


class WorkflowNextActionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_type: WorkflowActionType
    agent_id: str
    blocking_reason: str
    can_run: bool
    detail: str
    label: str
    priority: int
    stage_id: str
    stage_status: StageStatus
    stage_title: str


class WorkflowNextActionsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    quest_id: str
    action_count: int
    actions: list[WorkflowNextActionResponse]


def blocking_action_type(blocking_reason: str) -> BlockingActionType:
    if blocking_reason in {"inactive_provider", "missing_provider", "unsupported_provider"}:
        return "configure_provider"
    return "resolve_blocker"


def blocking_action_label(action_type: BlockingActionType, stage_title: str) -> str:
    match action_type:
        case "configure_provider":
            return f"Configure provider for {stage_title}"
        case "resolve_blocker":
            return f"Resolve blocker for {stage_title}"
        case unreachable:
            assert_never(unreachable)


def review_detail(stage: StageCard, node: WorkflowNodeResponse) -> str:
    return stage.review_notes or node.summary or "Review this stage output before continuing."


def review_action_required(review_state: GateStatus) -> bool:
    match review_state:
        case "pending_review":
            return True
        case "approved" | "not_required" | "rejected" | "waiting_for_completion":
            return False
        case unreachable:
            assert_never(unreachable)


def node_next_action(
    node: WorkflowNodeResponse,
    stage: StageCard,
    priority: int,
) -> WorkflowNextActionResponse:
    if review_action_required(node.review_state):
        return WorkflowNextActionResponse(
            action_type="review_stage",
            agent_id=node.agent_id,
            blocking_reason="human_review_required",
            can_run=False,
            detail=review_detail(stage, node),
            label=f"Review {node.title}",
            priority=priority,
            stage_id=node.stage_id,
            stage_status=node.status,
            stage_title=node.title,
        )
    if node.can_run:
        return WorkflowNextActionResponse(
            action_type="run_stage",
            agent_id=node.agent_id,
            blocking_reason="",
            can_run=True,
            detail="Stage is ready to run.",
            label=f"Run {node.title}",
            priority=priority,
            stage_id=node.stage_id,
            stage_status=node.status,
            stage_title=node.title,
        )
    match node.status:
        case StageStatus.RUNNING:
            return WorkflowNextActionResponse(
                action_type="wait_for_stage",
                agent_id=node.agent_id,
                blocking_reason="stage_already_running",
                can_run=False,
                detail="Wait for the current run to finish before taking the next action.",
                label=f"Wait for {node.title}",
                priority=priority,
                stage_id=node.stage_id,
                stage_status=node.status,
                stage_title=node.title,
            )
        case StageStatus.PENDING | StageStatus.BLOCKED | StageStatus.COMPLETE:
            action_type = blocking_action_type(node.blocking_reason)
            return WorkflowNextActionResponse(
                action_type=action_type,
                agent_id=node.agent_id,
                blocking_reason=node.blocking_reason,
                can_run=False,
                detail=node.blocking_detail,
                label=blocking_action_label(action_type, node.title),
                priority=priority,
                stage_id=node.stage_id,
                stage_status=node.status,
                stage_title=node.title,
            )
        case unreachable:
            assert_never(unreachable)


def node_needs_action(node: WorkflowNodeResponse) -> bool:
    return (
        review_action_required(node.review_state)
        or node.can_run
        or node_has_actionable_blocker(node)
    )


def node_has_actionable_blocker(node: WorkflowNodeResponse) -> bool:
    if not node.blocking_reason:
        return False
    match node.status:
        case StageStatus.COMPLETE:
            return node.blocking_reason != COMPLETED_STAGE_BLOCKING_REASON
        case StageStatus.PENDING | StageStatus.BLOCKED | StageStatus.RUNNING:
            return True
        case unreachable:
            assert_never(unreachable)


def build_next_actions(
    graph: WorkflowGraphResponse,
    stages: list[StageCard],
) -> WorkflowNextActionsResponse:
    stages_by_id = {stage.id: stage for stage in stages}
    actions = [
        node_next_action(node, stages_by_id[node.stage_id], priority)
        for priority, node in enumerate(graph.nodes, start=1)
        if node_needs_action(node)
    ]
    next_actions = actions[:1]
    return WorkflowNextActionsResponse(
        action_count=len(next_actions),
        actions=next_actions,
        quest_id=graph.quest.id,
    )


@router.get(
    "/quests/{quest_id}/workflow-next-actions",
    response_model=WorkflowNextActionsResponse,
)
def get_quest_workflow_next_actions(
    quest_id: str,
    context: Annotated[StageReadinessRequestContext, Depends(get_stage_readiness_context)],
) -> WorkflowNextActionsResponse:
    service = QuestService(context.session)
    try:
        quest = service.get_quest_for_user(quest_id, context.current_user)
        stages = service.list_stage_cards(quest.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return build_next_actions(build_workflow_graph(quest, stages, context), stages)
