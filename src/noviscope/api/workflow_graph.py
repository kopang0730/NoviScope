from dataclasses import dataclass
from typing import Annotated, Final, Literal, TypeAlias

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.api.dependencies import get_session
from noviscope.api.stage_runs import build_dependency_block_if_needed
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
    StageConfidence,
    normalize_stage_output_payload,
    stage_confidence,
)
from noviscope.models.quest import Quest, QuestStatus, StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

GateStatus: TypeAlias = Literal[
    "not_required",
    "waiting_for_completion",
    "pending_review",
    "approved",
    "rejected",
]

HUMAN_REVIEW_AGENT_IDS: Final = frozenset(
    {
        DEMAND_VALIDATOR_AGENT_ID,
        IDEA_GENERATOR_AGENT_ID,
        EXPERIMENT_PLANNER_AGENT_ID,
    }
)


@dataclass(frozen=True, slots=True)
class WorkflowDependency:
    source_agent_id: str
    target_agent_id: str
    relationship: str
    gate_required: bool


WORKFLOW_DEPENDENCIES: Final = (
    WorkflowDependency(
        source_agent_id=DEMAND_VALIDATOR_AGENT_ID,
        target_agent_id=LITERATURE_SCOUT_AGENT_ID,
        relationship="demand_validation_unlocks_literature",
        gate_required=True,
    ),
    WorkflowDependency(
        source_agent_id=DEMAND_VALIDATOR_AGENT_ID,
        target_agent_id=IDEA_GENERATOR_AGENT_ID,
        relationship="validated_demand_informs_hypotheses",
        gate_required=True,
    ),
    WorkflowDependency(
        source_agent_id=LITERATURE_SCOUT_AGENT_ID,
        target_agent_id=IDEA_GENERATOR_AGENT_ID,
        relationship="literature_evidence_informs_hypotheses",
        gate_required=False,
    ),
    WorkflowDependency(
        source_agent_id=IDEA_GENERATOR_AGENT_ID,
        target_agent_id=EXPERIMENT_PLANNER_AGENT_ID,
        relationship="selected_idea_unlocks_experiment_plan",
        gate_required=True,
    ),
    WorkflowDependency(
        source_agent_id=EXPERIMENT_PLANNER_AGENT_ID,
        target_agent_id=PAPER_MEETING_WRITER_AGENT_ID,
        relationship="reviewed_experiment_plan_unlocks_writing",
        gate_required=True,
    ),
)


class WorkflowQuestResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    initial_direction: str
    status: QuestStatus


class WorkflowNodeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    stage_id: str
    agent_id: str
    title: str
    order: int
    status: StageStatus
    confidence: StageConfidence
    summary: str
    can_run: bool
    blocking_reason: str | None
    blocking_detail: str | None
    human_review_required: bool
    review_state: GateStatus
    human_approved: bool | None


class WorkflowEdgeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    source_stage_id: str
    source_agent_id: str
    target_stage_id: str
    target_agent_id: str
    relationship: str
    gate_required: bool
    gate_status: GateStatus


class WorkflowGraphResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    quest: WorkflowQuestResponse
    nodes: list[WorkflowNodeResponse]
    edges: list[WorkflowEdgeResponse]


def build_workflow_graph(quest: Quest, stages: list[StageCard]) -> WorkflowGraphResponse:
    return WorkflowGraphResponse(
        edges=build_edges(stages),
        nodes=[build_node(stage, stages, order) for order, stage in enumerate(stages, start=1)],
        quest=WorkflowQuestResponse(
            id=quest.id,
            initial_direction=quest.initial_direction,
            status=quest.status,
            title=quest.title,
        ),
    )


def build_node(stage: StageCard, stages: list[StageCard], order: int) -> WorkflowNodeResponse:
    output_payload = normalize_stage_output_payload(stage.agent_id, stage.output_payload)
    dependency_payload = dependency_block_payload(stage, stages)
    can_run = (
        stage.status not in {StageStatus.COMPLETE, StageStatus.RUNNING}
        and not dependency_payload
    )
    return WorkflowNodeResponse(
        agent_id=stage.agent_id,
        blocking_detail=payload_string(dependency_payload, "blocking_detail"),
        blocking_reason=payload_string(dependency_payload, "blocking_reason"),
        can_run=can_run,
        confidence=stage_confidence(stage.agent_id, output_payload),
        human_approved=stage.human_approved,
        human_review_required=human_review_required(stage),
        id=stage.id,
        order=order,
        review_state=review_state(stage),
        stage_id=stage.id,
        status=stage.status,
        summary=stage.summary,
        title=stage.title,
    )


def build_edges(stages: list[StageCard]) -> list[WorkflowEdgeResponse]:
    stages_by_agent_id = {stage.agent_id: stage for stage in stages}
    edges: list[WorkflowEdgeResponse] = []
    for dependency in WORKFLOW_DEPENDENCIES:
        source_stage = stages_by_agent_id.get(dependency.source_agent_id)
        target_stage = stages_by_agent_id.get(dependency.target_agent_id)
        if source_stage is None or target_stage is None:
            continue
        edges.append(build_edge(dependency, source_stage, target_stage))
    return edges


def build_edge(
    dependency: WorkflowDependency,
    source_stage: StageCard,
    target_stage: StageCard,
) -> WorkflowEdgeResponse:
    return WorkflowEdgeResponse(
        gate_required=dependency.gate_required,
        gate_status=gate_status(dependency, source_stage),
        id=f"{source_stage.id}->{target_stage.id}",
        relationship=dependency.relationship,
        source_agent_id=source_stage.agent_id,
        source_stage_id=source_stage.id,
        target_agent_id=target_stage.agent_id,
        target_stage_id=target_stage.id,
    )


def dependency_block_payload(stage: StageCard, stages: list[StageCard]) -> JsonObject:
    block = build_dependency_block_if_needed(stage, stages)
    return block.evidence_payload if block is not None else {}


def payload_string(payload: JsonObject, key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def human_review_required(stage: StageCard) -> bool:
    return stage.agent_id in HUMAN_REVIEW_AGENT_IDS


def review_state(stage: StageCard) -> GateStatus:
    return gate_status_for_stage(stage, human_review_required(stage))


def gate_status(dependency: WorkflowDependency, source_stage: StageCard) -> GateStatus:
    return gate_status_for_stage(source_stage, dependency.gate_required)


def gate_status_for_stage(stage: StageCard, gate_required: bool) -> GateStatus:
    if not gate_required:
        return "not_required"
    if stage.status != StageStatus.COMPLETE:
        return "waiting_for_completion"
    if stage.agent_id == IDEA_GENERATOR_AGENT_ID:
        return "approved" if has_selected_idea(stage.output_payload) else "pending_review"
    if stage.human_approved is True:
        return "approved"
    if stage.human_approved is False:
        return "rejected"
    return "pending_review"


def has_selected_idea(output_payload: JsonObject) -> bool:
    selected_ideas = output_payload.get("selected_ideas")
    return isinstance(selected_ideas, list) and any(
        isinstance(selected_idea, dict) for selected_idea in selected_ideas
    )


@router.get("/quests/{quest_id}/workflow-graph", response_model=WorkflowGraphResponse)
def get_quest_workflow_graph(
    quest_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkflowGraphResponse:
    service = QuestService(session)
    try:
        quest = service.get_quest_for_user(quest_id, current_user)
        return build_workflow_graph(quest, service.list_stage_cards(quest.id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
