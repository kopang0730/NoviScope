from typing import Final, assert_never

from pydantic import JsonValue

from noviscope.agents.experiment_planner import has_selected_idea
from noviscope.api.experiment_gate_types import ExperimentGateCheck, ExperimentGateCheckStatus
from noviscope.models.quest import StageCard, StageStatus

EXPERIMENT_SETUP_FIELDS: Final = ("data_path", "code_repository", "environment_notes")
APPROVING_DEMAND_VERDICTS: Final = frozenset({"plausible", "verified"})
EXPERIMENT_PLAN_DETAIL_FIELDS: Final = (
    "datasets_needed",
    "baselines_to_reproduce",
    "metrics",
    "first_runnable_script_plan",
)
DEMAND_KEY, DEMAND_TITLE = "demand_validation", "Demand validation reviewed"
IDEA_KEY, IDEA_TITLE = "idea_selection", "Idea selected for experiment"
SETUP_KEY, SETUP_TITLE = "experiment_setup", "Experiment setup recorded"
PLAN_KEY, PLAN_TITLE = "experiment_plan", "Experiment plan approved"


def text_present(value: JsonValue | None) -> bool:
    match value:
        case str() as text:
            return bool(text.strip())
        case None | bool() | int() | float() | list() | dict():
            return False
        case unreachable:
            assert_never(unreachable)


def has_text_item(value: JsonValue | None) -> bool:
    match value:
        case list() as items:
            return any(text_present(item) for item in items)
        case None | str() | bool() | int() | float() | dict():
            return False
        case unreachable:
            assert_never(unreachable)


def has_text_value(value: JsonValue | None) -> bool:
    return text_present(value) or has_text_item(value)


def missing_stage_check(key: str, title: str, detail: str) -> ExperimentGateCheck:
    return ExperimentGateCheck(
        status=ExperimentGateCheckStatus.BLOCKED, detail=detail,
        key=key, stage_id=None, title=title,
    )


def demand_validation_check(stage: StageCard | None) -> ExperimentGateCheck:
    match stage:
        case None:
            return missing_stage_check(
                DEMAND_KEY,
                DEMAND_TITLE,
                "Demand validation stage is missing.",
            )
        case StageCard() as demand_stage:
            return demand_stage_check(demand_stage)
        case unreachable:
            assert_never(unreachable)


def demand_stage_check(stage: StageCard) -> ExperimentGateCheck:
    match stage.status:
        case StageStatus.COMPLETE:
            return demand_human_review_check(stage)
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            return ExperimentGateCheck(
                detail="Demand validation must complete before experiments.",
                key=DEMAND_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.BLOCKED,
                title=DEMAND_TITLE,
            )
        case unreachable:
            assert_never(unreachable)


def demand_human_review_check(stage: StageCard) -> ExperimentGateCheck:
    match stage.human_approved:
        case True:
            if not has_text_item(stage.evidence_payload.get("human_demand_sources")):
                return ExperimentGateCheck(
                    detail="Demand approval is missing human evidence sources.",
                    key=DEMAND_KEY,
                    stage_id=stage.id,
                    status=ExperimentGateCheckStatus.NEEDS_REVIEW,
                    title=DEMAND_TITLE,
                )
            verdict = stage.evidence_payload.get("human_demand_verdict")
            if not isinstance(verdict, str) or not verdict.strip():
                return ExperimentGateCheck(
                    detail="Demand approval is missing a human verdict.",
                    key=DEMAND_KEY,
                    stage_id=stage.id,
                    status=ExperimentGateCheckStatus.NEEDS_REVIEW,
                    title=DEMAND_TITLE,
                )
            if verdict in APPROVING_DEMAND_VERDICTS:
                return ExperimentGateCheck(
                    detail="Demand was approved with human evidence sources.",
                    key=DEMAND_KEY,
                    stage_id=stage.id,
                    status=ExperimentGateCheckStatus.PASS,
                    title=DEMAND_TITLE,
                )
            return ExperimentGateCheck(
                detail="Demand verdict must be plausible or verified before experiments.",
                key=DEMAND_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.BLOCKED,
                title=DEMAND_TITLE,
            )
        case False:
            return ExperimentGateCheck(
                detail="Human review did not approve the demand.",
                key=DEMAND_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.BLOCKED,
                title=DEMAND_TITLE,
            )
        case None:
            return ExperimentGateCheck(
                detail="Demand validation is complete but needs human review.",
                key=DEMAND_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.NEEDS_REVIEW,
                title=DEMAND_TITLE,
            )
        case unreachable:
            assert_never(unreachable)


def idea_selection_check(stage: StageCard | None) -> ExperimentGateCheck:
    match stage:
        case None:
            return missing_stage_check(
                IDEA_KEY,
                IDEA_TITLE,
                "Gap & hypothesis generator stage is missing.",
            )
        case StageCard() as idea_stage:
            return idea_stage_check(idea_stage)
        case unreachable:
            assert_never(unreachable)


def idea_stage_check(stage: StageCard) -> ExperimentGateCheck:
    match stage.status:
        case StageStatus.COMPLETE:
            return idea_human_review_check(stage)
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            return ExperimentGateCheck(
                detail="A generated idea must be selected before experiments.",
                key=IDEA_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.BLOCKED,
                title=IDEA_TITLE,
            )
        case unreachable:
            assert_never(unreachable)


def idea_human_review_check(stage: StageCard) -> ExperimentGateCheck:
    match stage.human_approved:
        case True:
            selected_ids = stage.output_payload.get("selected_idea_ids")
            if has_selected_idea(stage):
                return ExperimentGateCheck(
                    detail="At least one generated idea was selected by a human reviewer.",
                    key=IDEA_KEY,
                    stage_id=stage.id,
                    status=ExperimentGateCheckStatus.PASS,
                    title=IDEA_TITLE,
                )
            if has_text_item(selected_ids):
                return ExperimentGateCheck(
                    detail="Selected idea ids must match generated ideas.",
                    key=IDEA_KEY,
                    stage_id=stage.id,
                    status=ExperimentGateCheckStatus.NEEDS_REVIEW,
                    title=IDEA_TITLE,
                )
            return ExperimentGateCheck(
                detail="Idea stage was approved but no selected idea id was recorded.",
                key=IDEA_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.NEEDS_REVIEW,
                title=IDEA_TITLE,
            )
        case False:
            return ExperimentGateCheck(
                detail="Human review did not approve any idea for experiments.",
                key=IDEA_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.BLOCKED,
                title=IDEA_TITLE,
            )
        case None:
            return ExperimentGateCheck(
                detail="Generated ideas are complete but need human selection.",
                key=IDEA_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.NEEDS_REVIEW,
                title=IDEA_TITLE,
            )
        case unreachable:
            assert_never(unreachable)


def experiment_setup_check(stage: StageCard | None) -> ExperimentGateCheck:
    match stage:
        case None:
            return missing_stage_check(
                SETUP_KEY,
                SETUP_TITLE,
                "Experiment Planner stage is missing.",
            )
        case StageCard() as experiment_stage:
            return experiment_setup_stage_check(experiment_stage)
        case unreachable:
            assert_never(unreachable)


def experiment_setup_stage_check(stage: StageCard) -> ExperimentGateCheck:
    fields_ready = all(
        text_present(stage.input_payload.get(field)) for field in EXPERIMENT_SETUP_FIELDS
    )
    if fields_ready:
        return ExperimentGateCheck(
            detail="Data path, code repository, and environment notes are recorded.",
            key=SETUP_KEY,
            stage_id=stage.id,
            status=ExperimentGateCheckStatus.PASS,
            title=SETUP_TITLE,
        )
    return ExperimentGateCheck(
        detail="Record data path, code repository, and environment notes first.",
        key=SETUP_KEY,
        stage_id=stage.id,
        status=ExperimentGateCheckStatus.BLOCKED,
        title=SETUP_TITLE,
    )


def experiment_plan_check(stage: StageCard | None) -> ExperimentGateCheck:
    match stage:
        case None:
            return missing_stage_check(
                PLAN_KEY,
                PLAN_TITLE,
                "Experiment Planner stage is missing.",
            )
        case StageCard() as experiment_stage:
            return experiment_plan_stage_check(experiment_stage)
        case unreachable:
            assert_never(unreachable)


def experiment_plan_stage_check(stage: StageCard) -> ExperimentGateCheck:
    match stage.status:
        case StageStatus.COMPLETE:
            return experiment_plan_human_review_check(stage)
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            return ExperimentGateCheck(
                detail="Experiment Planner must complete before experimental execution.",
                key=PLAN_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.BLOCKED,
                title=PLAN_TITLE,
            )
        case unreachable:
            assert_never(unreachable)


def has_experiment_plan_output(stage: StageCard) -> bool:
    return text_present(stage.output_payload.get("summary")) and all(
        has_text_value(stage.output_payload.get(field)) for field in EXPERIMENT_PLAN_DETAIL_FIELDS
    )


def experiment_plan_human_review_check(stage: StageCard) -> ExperimentGateCheck:
    match stage.human_approved:
        case True:
            if not has_experiment_plan_output(stage):
                return ExperimentGateCheck(
                    detail="Experiment plan approval is missing generated plan details.",
                    key=PLAN_KEY,
                    stage_id=stage.id,
                    status=ExperimentGateCheckStatus.NEEDS_REVIEW,
                    title=PLAN_TITLE,
                )
            return ExperimentGateCheck(
                detail="Experiment plan is complete and human-approved.",
                key=PLAN_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.PASS,
                title=PLAN_TITLE,
            )
        case False:
            return ExperimentGateCheck(
                detail="Human review rejected the experiment plan.",
                key=PLAN_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.BLOCKED,
                title=PLAN_TITLE,
            )
        case None:
            return ExperimentGateCheck(
                detail="Experiment plan is complete but needs human approval.",
                key=PLAN_KEY,
                stage_id=stage.id,
                status=ExperimentGateCheckStatus.NEEDS_REVIEW,
                title=PLAN_TITLE,
            )
        case unreachable:
            assert_never(unreachable)
