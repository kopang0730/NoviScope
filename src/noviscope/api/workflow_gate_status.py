from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, Literal, TypeAlias, assert_never

from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
)
from noviscope.models.quest import StageCard, StageStatus

GateStatus: TypeAlias = Literal[
    "not_required",
    "waiting_for_completion",
    "pending_review",
    "approved",
    "rejected",
]
NextHumanAction: TypeAlias = Literal[
    "none",
    "run_stage",
    "wait_for_completion",
    "review_demand",
    "select_idea",
    "review_experiment_plan",
    "revise_stage",
]

HUMAN_REVIEW_AGENT_IDS: Final = frozenset(
    {
        DEMAND_VALIDATOR_AGENT_ID,
        IDEA_GENERATOR_AGENT_ID,
        EXPERIMENT_PLANNER_AGENT_ID,
    }
)
PENDING_REVIEW_ACTIONS: Final[Mapping[str, NextHumanAction]] = MappingProxyType(
    {
        DEMAND_VALIDATOR_AGENT_ID: "review_demand",
        IDEA_GENERATOR_AGENT_ID: "select_idea",
        EXPERIMENT_PLANNER_AGENT_ID: "review_experiment_plan",
    }
)


def human_review_required(stage: StageCard) -> bool:
    return stage.agent_id in HUMAN_REVIEW_AGENT_IDS


def review_state(stage: StageCard) -> GateStatus:
    return gate_status_for_stage(stage, human_review_required(stage))


def gate_status(gate_required: bool, source_stage: StageCard) -> GateStatus:
    return gate_status_for_stage(source_stage, gate_required)


def gate_status_for_stage(stage: StageCard, gate_required: bool) -> GateStatus:
    if not gate_required:
        return "not_required"
    match stage.status:
        case StageStatus.PENDING | StageStatus.BLOCKED | StageStatus.RUNNING:
            return "waiting_for_completion"
        case StageStatus.COMPLETE:
            return completed_gate_status(stage)
        case unreachable:
            assert_never(unreachable)


def completed_gate_status(stage: StageCard) -> GateStatus:
    if stage.agent_id == IDEA_GENERATOR_AGENT_ID:
        return "approved" if has_selected_idea(stage.output_payload) else "pending_review"
    if stage.human_approved is True:
        return "approved"
    if stage.human_approved is False:
        return "rejected"
    return "pending_review"


def next_human_action(stage: StageCard, can_run: bool) -> NextHumanAction:
    match stage.status:
        case StageStatus.PENDING | StageStatus.BLOCKED:
            return "run_stage" if can_run else "none"
        case StageStatus.RUNNING:
            return "wait_for_completion"
        case StageStatus.COMPLETE:
            return completed_stage_action(stage)
        case unreachable:
            assert_never(unreachable)


def completed_stage_action(stage: StageCard) -> NextHumanAction:
    state = review_state(stage)
    match state:
        case "approved" | "not_required":
            return "none"
        case "pending_review":
            return PENDING_REVIEW_ACTIONS.get(stage.agent_id, "none")
        case "rejected":
            return "revise_stage"
        case "waiting_for_completion":
            return "wait_for_completion"
        case unreachable:
            assert_never(unreachable)


def has_selected_idea(output_payload: JsonObject) -> bool:
    selected_ideas = output_payload.get("selected_ideas")
    return isinstance(selected_ideas, list) and any(
        isinstance(selected_idea, dict) for selected_idea in selected_ideas
    )
