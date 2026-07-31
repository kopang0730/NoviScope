from dataclasses import dataclass
from typing import Annotated, ClassVar, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlmodel import Session

from noviscope.agents.experiment_planner import read_experiment_setup_inputs
from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    EXPERIMENT_PLANNER_AGENT_ID,
    StageConfidence,
    stage_confidence,
)
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

INCOMPLETE_STAGE_REASON: Final = (
    "Experiment Planner must complete before experiment plan matrix rows are available."
)
WRONG_STAGE_REASON: Final = "This stage does not expose Experiment Planner outputs."
HUMAN_REVIEW_CHECKLIST: Final[tuple[str, ...]] = (
    "Verify dataset paths are accessible on the lab server before running experiments.",
    "Confirm baseline code, license, commit, and environment notes are reproducible.",
    "Check that metrics, ablations, expected tables, and figures match the selected idea.",
    "Treat every listed failure risk as unresolved until a human reviews it.",
)


@dataclass(frozen=True, slots=True)
class PlanSectionSpec:
    section_id: str
    title: str
    payload_key: str


PLAN_SECTION_SPECS: Final[tuple[PlanSectionSpec, ...]] = (
    PlanSectionSpec("datasets_needed", "Datasets needed", "datasets_needed"),
    PlanSectionSpec("baselines_to_reproduce", "Baselines to reproduce", "baselines_to_reproduce"),
    PlanSectionSpec("metrics", "Metrics", "metrics"),
    PlanSectionSpec("ablation_variables", "Ablation variables", "ablation_variables"),
    PlanSectionSpec("expected_tables", "Expected tables", "expected_tables"),
    PlanSectionSpec("expected_figures", "Expected figures", "expected_figures"),
    PlanSectionSpec(
        "first_runnable_script_plan",
        "First runnable script plan",
        "first_runnable_script_plan",
    ),
)


class ExperimentSetupInputsResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    code_repository: str
    data_path: str
    environment_notes: str


class ExperimentPlanSectionResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    items: list[str]
    section_id: str
    title: str


class ExperimentPlanMatrixResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    confidence: StageConfidence
    compute_requirements: str
    data_availability_status: str
    failure_risks: list[str]
    human_review_checklist: tuple[str, ...]
    no_experiment_results: bool
    plan_only: bool
    plan_sections: list[ExperimentPlanSectionResponse]
    requires_human_review: bool
    setup_inputs: ExperimentSetupInputsResponse
    source_stage_ids: dict[str, str]
    stage_id: str
    status: StageStatus
    summary: str
    unavailable_reason: str
    warnings: list[str]


def string_items(items: list[JsonValue]) -> list[str]:
    values: list[str] = []
    for item in items:
        match item:
            case str() as value:
                if value:
                    values.append(value)
            case None | bool() | int() | float() | list() | dict():
                continue
            case unreachable:
                assert_never(unreachable)
    return values


def read_text(payload: JsonObject, key: str) -> str:
    value = payload.get(key)
    match value:
        case str() as text:
            return text
        case None | bool() | int() | float() | list() | dict():
            return ""
        case unreachable:
            assert_never(unreachable)


def read_string_list(payload: JsonObject, key: str) -> list[str]:
    value = payload.get(key)
    match value:
        case list() as items:
            return string_items(items)
        case None | str() | bool() | int() | float() | dict():
            return []
        case unreachable:
            assert_never(unreachable)


def read_source_stage_ids(payload: JsonObject) -> dict[str, str]:
    value = payload.get("source_stage_ids")
    match value:
        case dict() as mapping:
            return {
                key: item
                for key, item in mapping.items()
                if isinstance(key, str) and isinstance(item, str)
            }
        case None | str() | bool() | int() | float() | list():
            return {}
        case unreachable:
            assert_never(unreachable)


def setup_inputs(stage: StageCard) -> ExperimentSetupInputsResponse:
    setup = read_experiment_setup_inputs(stage.input_payload)
    return ExperimentSetupInputsResponse(
        code_repository=read_text(setup, "code_repository"),
        data_path=read_text(setup, "data_path"),
        environment_notes=read_text(setup, "environment_notes"),
    )


def plan_section(payload: JsonObject, spec: PlanSectionSpec) -> ExperimentPlanSectionResponse:
    return ExperimentPlanSectionResponse(
        items=read_string_list(payload, spec.payload_key),
        section_id=spec.section_id,
        title=spec.title,
    )


def empty_response(stage: StageCard, reason: str) -> ExperimentPlanMatrixResponse:
    return ExperimentPlanMatrixResponse(
        confidence=stage_confidence(stage.agent_id, stage.output_payload),
        compute_requirements="",
        data_availability_status="",
        failure_risks=[],
        human_review_checklist=HUMAN_REVIEW_CHECKLIST,
        no_experiment_results=True,
        plan_only=True,
        plan_sections=[],
        requires_human_review=True,
        setup_inputs=setup_inputs(stage),
        source_stage_ids=read_source_stage_ids(stage.output_payload),
        stage_id=stage.id,
        status=stage.status,
        summary=stage.summary,
        unavailable_reason=reason,
        warnings=[],
    )


def build_experiment_plan_matrix(stage: StageCard) -> ExperimentPlanMatrixResponse:
    if stage.agent_id != EXPERIMENT_PLANNER_AGENT_ID:
        return empty_response(stage, WRONG_STAGE_REASON)
    if stage.status != StageStatus.COMPLETE:
        return empty_response(stage, INCOMPLETE_STAGE_REASON)

    output = stage.output_payload
    return ExperimentPlanMatrixResponse(
        confidence=stage_confidence(stage.agent_id, output),
        compute_requirements=read_text(output, "compute_requirements"),
        data_availability_status=read_text(output, "data_availability_status"),
        failure_risks=read_string_list(output, "failure_risks"),
        human_review_checklist=HUMAN_REVIEW_CHECKLIST,
        no_experiment_results=True,
        plan_only=True,
        plan_sections=[plan_section(output, spec) for spec in PLAN_SECTION_SPECS],
        requires_human_review=True,
        setup_inputs=setup_inputs(stage),
        source_stage_ids=read_source_stage_ids(output),
        stage_id=stage.id,
        status=stage.status,
        summary=read_text(output, "summary") or stage.summary,
        unavailable_reason="",
        warnings=read_string_list(output, "warnings"),
    )


@router.get(
    "/stages/{stage_id}/experiment-plan-matrix",
    response_model=ExperimentPlanMatrixResponse,
)
def get_experiment_plan_matrix(
    stage_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExperimentPlanMatrixResponse:
    service = QuestService(session)
    try:
        stage = service.get_stage_card_for_user(stage_id, current_user)
        return build_experiment_plan_matrix(stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
