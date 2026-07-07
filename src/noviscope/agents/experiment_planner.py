import json
from dataclasses import dataclass
from typing import Literal, Protocol, assert_never

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError

from noviscope.agents.prompt_compaction import compact_prompt_payload
from noviscope.agents.provider_chat import (
    ChatCompletionPayload,
    ProviderChatClient,
    ProviderChatRequest,
    ProviderChatRunError,
)
from noviscope.agents.stage_runner import StageRunContext, StageRunner, StageRunResult
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import EXPERIMENT_PLANNER_AGENT_ID, IDEA_GENERATOR_AGENT_ID
from noviscope.models.provider import ProviderKind
from noviscope.models.quest import StageCard, StageStatus

MAX_TEXT_FIELD_CHARS = 700
MAX_SELECTED_IDEAS_FOR_PROMPT = 3
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


class ExperimentPlannerRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_id: str
    quest_title: str
    initial_direction: str
    provider_id: str
    provider_name: str
    provider_kind: ProviderKind
    base_url: str
    model: str
    api_key: SecretStr
    selected_ideas: list[JsonObject]
    idea_stage_output: JsonObject
    data_path: str
    code_repository: str
    environment_notes: str
    source_stage_ids: JsonObject


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


class ExperimentPlannerRunner(Protocol):
    def run(self, request: ExperimentPlannerRequest) -> ExperimentPlanOutput: ...


@dataclass(frozen=True, slots=True)
class ExperimentPlannerRunError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


class OpenAICompatibleExperimentPlannerRunner:
    def __init__(self, chat_client: ProviderChatClient | None = None) -> None:
        self._chat_client = chat_client or ProviderChatClient()

    def run(self, request: ExperimentPlannerRequest) -> ExperimentPlanOutput:
        match request.provider_kind:
            case ProviderKind.OPENAI_COMPATIBLE | ProviderKind.CUSTOM | ProviderKind.ANTHROPIC:
                return self._run_provider_chat(request)
            case unreachable:
                assert_never(unreachable)

    def _run_provider_chat(
        self,
        request: ExperimentPlannerRequest,
    ) -> ExperimentPlanOutput:
        payload = build_chat_completion_payload(request)
        try:
            raw_content = self._chat_client.complete(
                ProviderChatRequest(
                    api_key=request.api_key,
                    base_url=request.base_url,
                    messages=payload["messages"],
                    model=request.model,
                    provider_kind=request.provider_kind,
                    temperature=payload["temperature"],
                )
            )
        except ProviderChatRunError as exc:
            raise ExperimentPlannerRunError(str(exc)) from exc
        return parse_experiment_plan_output(raw_content, request)


@dataclass(frozen=True, slots=True)
class ExperimentPlannerStageRunner(StageRunner):
    experiment_runner: ExperimentPlannerRunner

    @property
    def agent_id(self) -> str:
        return EXPERIMENT_PLANNER_AGENT_ID

    @property
    def supported_provider_kinds(self) -> frozenset[ProviderKind]:
        return frozenset(
            {ProviderKind.ANTHROPIC, ProviderKind.OPENAI_COMPATIBLE, ProviderKind.CUSTOM}
        )

    def build_input_payload(self, context: StageRunContext) -> JsonObject:
        idea_stage = find_stage(context.workflow_stages, IDEA_GENERATOR_AGENT_ID)
        selected_ideas = read_selected_ideas(idea_stage)
        setup = read_experiment_setup_inputs(context.stage.input_payload)
        return {
            "agent_id": context.stage.agent_id,
            "code_repository": setup["code_repository"],
            "data_path": setup["data_path"],
            "environment_notes": setup["environment_notes"],
            "provider_id": context.provider.id,
            "provider_model": context.provider.model,
            "provider_name": context.provider.name,
            "selected_idea_count": len(selected_ideas),
            "source_stage_ids": build_source_stage_ids(idea_stage),
        }

    def run(self, context: StageRunContext) -> StageRunResult:
        idea_stage = require_selected_idea_stage(context.workflow_stages)
        selected_ideas = read_selected_ideas(idea_stage)
        setup = read_experiment_setup_inputs(context.stage.input_payload)
        source_stage_ids = build_source_stage_ids(idea_stage)
        input_payload = self.build_input_payload(context)

        output = self.experiment_runner.run(
            ExperimentPlannerRequest(
                api_key=context.provider.api_key,
                base_url=context.provider.base_url,
                code_repository=setup["code_repository"],
                data_path=setup["data_path"],
                environment_notes=setup["environment_notes"],
                idea_stage_output=compact_payload(idea_stage.output_payload),
                initial_direction=context.quest.initial_direction,
                model=context.provider.model,
                provider_id=context.provider.id,
                provider_kind=context.provider.kind,
                provider_name=context.provider.name,
                quest_title=context.quest.title,
                selected_ideas=selected_ideas[:MAX_SELECTED_IDEAS_FOR_PROMPT],
                source_stage_ids=source_stage_ids,
                stage_id=context.stage.id,
            )
        )

        return StageRunResult(
            confidence=output.confidence,
            evidence_payload=build_stage_evidence_payload(context, output, selected_ideas),
            input_payload=input_payload,
            output_payload=build_stage_output_payload(output),
            summary=output.summary,
        )


def build_chat_completion_payload(request: ExperimentPlannerRequest) -> ChatCompletionPayload:
    prompt_payload = {
        "experiment_setup": {
            "code_repository": request.code_repository,
            "data_path": request.data_path,
            "environment_notes": request.environment_notes,
        },
        "idea_stage_output": compact_payload(request.idea_stage_output),
        "quest": {
            "initial_direction": request.initial_direction,
            "title": request.quest_title,
        },
        "selected_ideas": [
            compact_payload(idea) for idea in request.selected_ideas[:MAX_SELECTED_IDEAS_FOR_PROMPT]
        ],
        "source_stage_ids": request.source_stage_ids,
    }
    return {
        "messages": [
            {
                "content": (
                    "You are NoviScope's Experiment Planner. Return only valid JSON with "
                    "keys summary, confidence, data_availability_status, datasets_needed, "
                    "baselines_to_reproduce, metrics, ablation_variables, expected_tables, "
                    "expected_figures, compute_requirements, first_runnable_script_plan, "
                    "failure_risks. Design an executable experiment plan for the selected "
                    "idea using the provided data path, code repository, and environment "
                    "notes. Do not claim experiments have run. Do not invent metric values, "
                    "benchmark scores, tables, figures, or validation results. Keep confidence "
                    "cautious because this stage plans experiments but does not execute them."
                ),
                "role": "system",
            },
            {
                "content": json.dumps(prompt_payload, ensure_ascii=False),
                "role": "user",
            },
        ],
        "model": request.model,
        "temperature": 0.2,
    }


def parse_experiment_plan_output(
    raw_content: str,
    request: ExperimentPlannerRequest,
) -> ExperimentPlanOutput:
    try:
        parsed_content = json.loads(raw_content)
        output = ExperimentPlanOutput.model_validate(
            {
                **parsed_content,
                "raw_response": raw_content,
                "source_stage_ids": request.source_stage_ids,
            }
        )
    except (json.JSONDecodeError, TypeError, ValidationError):
        return ExperimentPlanOutput(
            ablation_variables=[],
            baselines_to_reproduce=[],
            compute_requirements="",
            confidence="low",
            data_availability_status="unknown",
            datasets_needed=[],
            expected_figures=[],
            expected_tables=[],
            failure_risks=["The model response was not valid structured JSON."],
            first_runnable_script_plan=[],
            metrics=[],
            raw_response=raw_content,
            source_stage_ids=request.source_stage_ids,
            summary="The model response was not valid structured JSON.",
            warnings=["The model response was not valid structured JSON.", PLAN_ONLY_WARNING],
        )
    return constrain_plan_output(output)


def constrain_plan_output(output: ExperimentPlanOutput) -> ExperimentPlanOutput:
    warnings = list(output.warnings)
    if PLAN_ONLY_WARNING not in warnings:
        warnings.append(PLAN_ONLY_WARNING)
    return output.model_copy(
        update={
            "confidence": cap_confidence(output.confidence),
            "warnings": warnings,
        }
    )


def cap_confidence(confidence: str) -> Confidence:
    if confidence == "high":
        return "medium"
    if confidence == "medium":
        return "medium"
    return "low"


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
        "failure_risks": output.failure_risks,
        "first_runnable_script_plan": output.first_runnable_script_plan,
        "metrics": output.metrics,
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
    return compact_prompt_payload(
        payload,
        max_list_items=8,
        max_text_chars=MAX_TEXT_FIELD_CHARS,
    )


def normalize_dict(value: dict[object, object]) -> JsonObject:
    normalized: JsonObject = {}
    for key, item in value.items():
        if isinstance(key, str) and (
            isinstance(item, str | int | float | bool | dict | list) or item is None
        ):
            normalized[key] = item
    return normalized


def string_value(value: object) -> str:
    return value if isinstance(value, str) else ""


def get_experiment_planner_runner() -> ExperimentPlannerRunner:
    return OpenAICompatibleExperimentPlannerRunner()
