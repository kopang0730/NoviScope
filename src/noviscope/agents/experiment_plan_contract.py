from dataclasses import dataclass
from typing import Literal, assert_never

from pydantic import BaseModel, ConfigDict, JsonValue

from noviscope.agents.stage_runner import StageRunContext
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import IDEA_GENERATOR_AGENT_ID
from noviscope.models.quest import StageCard, StageStatus

MAX_TEXT_FIELD_CHARS = 700
PLAN_ONLY_WARNING = "No experiment has run. This output is an executable plan only."

Confidence = Literal["high", "medium", "low"]
DataAvailabilityStatus = Literal[
    "ready",
    "needs_data_path",
    "needs_code_repository",
    "needs_environment_notes",
    "blocked_missing_inputs",
    "unknown",
]


class ExperimentPlanOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: str
    confidence: Confidence
    data_availability_status: DataAvailabilityStatus
    datasets_needed: list[str]
    baselines_to_reproduce: list[str]
    metrics: list[str]
    ablation_variables: list[str]
    expected_tables: list[str]
    expected_figures: list[str]
    compute_requirements: str
    first_runnable_script_plan: list[str]
    failure_risks: list[str]
    source_stage_ids: JsonObject
    raw_response: str
    warnings: list[str] = []


@dataclass(frozen=True, slots=True)
class ExperimentPlannerRunError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


def build_stage_output_payload(output: ExperimentPlanOutput) -> JsonObject:
    return {
        "ablation_variables": output.ablation_variables,
        "baselines_to_reproduce": output.baselines_to_reproduce,
        "compute_requirements": output.compute_requirements,
        "confidence": output.confidence,
        "data_availability_status": output.data_availability_status,
        "datasets_needed": output.datasets_needed,
        "expected_figures": output.expected_figures,
        "expected_tables": output.expected_tables,
        "experiment_results_status": "not_run",
        "failure_risks": output.failure_risks,
        "first_runnable_script_plan": output.first_runnable_script_plan,
        "metrics": output.metrics,
        "no_experiment_results": True,
        "plan_only": True,
        "raw_response": output.raw_response,
        "source_stage_ids": output.source_stage_ids,
        "summary": output.summary,
        "warnings": output.warnings,
    }


def build_stage_evidence_payload(
    context: StageRunContext,
    output: ExperimentPlanOutput,
    selected_ideas: list[JsonObject],
) -> JsonObject:
    return {
        "can_run": True,
        "data_availability_status": output.data_availability_status,
        "no_experiment_results": True,
        "plan_only": True,
        "provider_id": context.provider.id,
        "provider_model": context.provider.model,
        "provider_name": context.provider.name,
        "requires_human_review": True,
        "selected_idea_count": len(selected_ideas),
        "source_stage_ids": output.source_stage_ids,
        "warning_count": len(output.warnings),
    }


def find_stage(stages: tuple[StageCard, ...], agent_id: str) -> StageCard | None:
    return next((stage for stage in stages if stage.agent_id == agent_id), None)


def require_selected_idea_stage(stages: tuple[StageCard, ...]) -> StageCard:
    stage = find_stage(stages, IDEA_GENERATOR_AGENT_ID)
    if stage is None or stage.status != StageStatus.COMPLETE:
        raise ExperimentPlannerRunError(
            "Gap & hypothesis generator must complete before Experiment Planner runs."
        )
    if not has_selected_idea(stage):
        raise ExperimentPlannerRunError(
            "Select and approve one generated idea before Experiment Planner runs."
        )
    return stage


def has_selected_idea(stage: StageCard) -> bool:
    selected_idea_ids = stage.output_payload.get("selected_idea_ids")
    idea_values = stage.output_payload.get("ideas")
    if stage.human_approved is not True or not isinstance(selected_idea_ids, list):
        return False
    if not isinstance(idea_values, list):
        return False
    selected_ids = {
        idea_id for idea_id in selected_idea_ids if isinstance(idea_id, str) and idea_id
    }
    return any(
        isinstance(value, dict)
        and isinstance(value.get("idea_id"), str)
        and value.get("idea_id") in selected_ids
        for value in idea_values
    )


def read_selected_ideas(stage: StageCard | None) -> list[JsonObject]:
    if stage is None:
        return []
    selected_idea_ids = stage.output_payload.get("selected_idea_ids")
    idea_values = stage.output_payload.get("ideas")
    if not isinstance(selected_idea_ids, list) or not isinstance(idea_values, list):
        return []
    selected_ids = {
        idea_id for idea_id in selected_idea_ids if isinstance(idea_id, str) and idea_id
    }
    selected_ideas: list[JsonObject] = []
    for value in idea_values:
        if not isinstance(value, dict):
            continue
        idea_id = value.get("idea_id")
        if isinstance(idea_id, str) and idea_id in selected_ids:
            selected_ideas.append(compact_payload(normalize_dict(value)))
    return selected_ideas


def read_experiment_setup_inputs(payload: JsonObject) -> JsonObject:
    return {
        "code_repository": string_value(payload.get("code_repository")).strip(),
        "data_path": string_value(payload.get("data_path")).strip(),
        "environment_notes": string_value(payload.get("environment_notes")).strip(),
    }


def missing_experiment_setup_inputs(payload: JsonObject) -> list[str]:
    setup = read_experiment_setup_inputs(payload)
    return [
        field_name
        for field_name in ("data_path", "code_repository", "environment_notes")
        if not setup[field_name]
    ]


def build_source_stage_ids(idea_stage: StageCard | None) -> JsonObject:
    return {"idea_generator": idea_stage.id if idea_stage is not None else ""}


def compact_payload(payload: JsonObject) -> JsonObject:
    compacted: JsonObject = {}
    for key, value in payload.items():
        if key == "raw_response":
            continue
        match value:
            case str():
                compacted[key] = trim_text(value)
            case list():
                compacted[key] = [
                    trim_text(item) if isinstance(item, str) else item
                    for item in value[:8]
                    if isinstance(item, str | int | float | bool | dict)
                ]
            case int() | float() | bool() | dict() | None:
                compacted[key] = value
            case unreachable:
                assert_never(unreachable)
    return compacted


def normalize_dict(value: JsonObject) -> JsonObject:
    normalized: JsonObject = {}
    for key, item in value.items():
        if isinstance(item, str | int | float | bool | dict | list) or item is None:
            normalized[key] = item
    return normalized


def trim_text(value: str) -> str:
    return " ".join(value.split())[:MAX_TEXT_FIELD_CHARS]


def string_value(value: JsonValue | None) -> str:
    return value if isinstance(value, str) else ""
