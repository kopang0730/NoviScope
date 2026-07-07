from dataclasses import dataclass
from typing import Final

from noviscope.agents.experiment_planner import (
    has_selected_idea,
    missing_experiment_setup_inputs,
)
from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.models.quest import StageCard, StageStatus

ACCEPTED_HUMAN_DEMAND_VERDICTS: Final = frozenset({"plausible", "verified"})


@dataclass(frozen=True, slots=True)
class StageBlock:
    summary: str
    evidence_payload: JsonObject


def build_literature_dependency_block() -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": "Complete Demand validation before running Literature Scout.",
            "blocking_reason": "demand_validation_incomplete",
            "can_run": False,
        },
        summary="Literature Scout is blocked until Demand validation is complete.",
    )


def build_demand_review_block(stage_title: str) -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": (
                f"Approve Demand validation before running {stage_title}. If the demand was "
                "rejected, revise or rerun Demand validation first."
            ),
            "blocking_reason": "demand_validation_review_required",
            "can_run": False,
        },
        summary=f"{stage_title} is blocked until Demand validation is human-approved.",
    )


def build_demand_evidence_review_block(stage_title: str) -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": (
                "Record at least one plausible or verified human demand evidence source "
                f"before running {stage_title}."
            ),
            "blocking_reason": "demand_evidence_review_required",
            "can_run": False,
        },
        summary=f"{stage_title} is blocked until human demand evidence is recorded.",
    )


def build_gap_dependency_block(missing_stage_names: list[str]) -> StageBlock:
    missing = ", ".join(missing_stage_names)
    return StageBlock(
        evidence_payload={
            "blocking_detail": f"Complete {missing} before running Gap & hypothesis generator.",
            "blocking_reason": "gap_prerequisites_incomplete",
            "can_run": False,
            "missing_prerequisites": missing_stage_names,
        },
        summary="Gap & hypothesis generator is blocked until prerequisite stages complete.",
    )


def build_experiment_dependency_block() -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": (
                "Complete Gap & hypothesis generator, then select and approve one idea before "
                "running Experiment Planner."
            ),
            "blocking_reason": "experiment_prerequisites_incomplete",
            "can_run": False,
        },
        summary="Experiment Planner is blocked until a generated idea is selected.",
    )


def build_experiment_setup_block(missing_inputs: list[str]) -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": (
                "Add data path, code repository, and environment notes before generating an "
                "experiment plan."
            ),
            "blocking_reason": "missing_experiment_inputs",
            "can_run": False,
            "missing_inputs": missing_inputs,
        },
        summary="Experiment Planner needs experiment setup inputs before it can run.",
    )


def build_paper_dependency_block() -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": "Complete Experiment Planner before generating paper artifacts.",
            "blocking_reason": "paper_prerequisites_incomplete",
            "can_run": False,
        },
        summary="Paper & Meeting Writer is blocked until Experiment Planner completes.",
    )


def build_paper_review_block() -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": (
                "Approve Experiment Planner before generating paper or meeting artifacts. "
                "Drafts must not rely on an unreviewed experiment plan."
            ),
            "blocking_reason": "experiment_planner_review_required",
            "can_run": False,
        },
        summary="Paper & Meeting Writer is blocked until Experiment Planner is human-approved.",
    )


def build_runner_block(stage: StageCard) -> StageBlock:
    return StageBlock(
        evidence_payload={
            "blocking_detail": "No runner has been implemented for this workflow stage yet.",
            "blocking_reason": "runner_not_implemented",
            "can_run": False,
        },
        summary=f"{stage.title} is not automated in this MVP yet.",
    )


def build_dependency_block_if_needed(
    stage: StageCard,
    stages: list[StageCard],
) -> StageBlock | None:
    demand_stage = find_workflow_stage(stages, DEMAND_VALIDATOR_AGENT_ID)
    completed_agent_ids = {
        workflow_stage.agent_id
        for workflow_stage in stages
        if workflow_stage.status == StageStatus.COMPLETE
    }
    if (
        stage.agent_id == LITERATURE_SCOUT_AGENT_ID
        and DEMAND_VALIDATOR_AGENT_ID not in completed_agent_ids
    ):
        return build_literature_dependency_block()
    if stage.agent_id != DEMAND_VALIDATOR_AGENT_ID and demand_stage is not None:
        if demand_stage.status == StageStatus.COMPLETE and demand_stage.human_approved is not True:
            return build_demand_review_block(stage.title)
        if (
            demand_stage.status == StageStatus.COMPLETE
            and demand_stage.human_approved is True
            and not has_recorded_human_demand_evidence(demand_stage)
        ):
            return build_demand_evidence_review_block(stage.title)
    if stage.agent_id == IDEA_GENERATOR_AGENT_ID:
        missing_stage_names: list[str] = []
        if DEMAND_VALIDATOR_AGENT_ID not in completed_agent_ids:
            missing_stage_names.append("Demand validation")
        if LITERATURE_SCOUT_AGENT_ID not in completed_agent_ids:
            missing_stage_names.append("Literature Scout")
        if missing_stage_names:
            return build_gap_dependency_block(missing_stage_names)
    if stage.agent_id == EXPERIMENT_PLANNER_AGENT_ID:
        idea_stage = find_workflow_stage(stages, IDEA_GENERATOR_AGENT_ID)
        if (
            idea_stage is None
            or idea_stage.status != StageStatus.COMPLETE
            or not has_selected_idea(idea_stage)
        ):
            return build_experiment_dependency_block()
        missing_inputs = missing_experiment_setup_inputs(stage.input_payload)
        if missing_inputs:
            return build_experiment_setup_block(missing_inputs)
    if stage.agent_id == PAPER_MEETING_WRITER_AGENT_ID:
        experiment_stage = find_workflow_stage(stages, EXPERIMENT_PLANNER_AGENT_ID)
        if experiment_stage is None or experiment_stage.status != StageStatus.COMPLETE:
            return build_paper_dependency_block()
        if experiment_stage.human_approved is not True:
            return build_paper_review_block()
    return None


def find_workflow_stage(stages: list[StageCard], agent_id: str) -> StageCard | None:
    return next(
        (workflow_stage for workflow_stage in stages if workflow_stage.agent_id == agent_id),
        None,
    )


def has_recorded_human_demand_evidence(stage: StageCard) -> bool:
    verdict = stage.evidence_payload.get("human_demand_verdict")
    if not isinstance(verdict, str) or verdict not in ACCEPTED_HUMAN_DEMAND_VERDICTS:
        return False

    sources = stage.evidence_payload.get("human_demand_sources")
    if not isinstance(sources, list):
        return False

    return any(isinstance(source, str) and source.strip() for source in sources)
