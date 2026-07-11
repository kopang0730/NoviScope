import json
from dataclasses import dataclass
from typing import Protocol, assert_never

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError

from noviscope.agents.experiment_plan_contract import (
    PLAN_ONLY_WARNING,
    Confidence,
    ExperimentPlannerRunError,
    ExperimentPlanOutput,
    build_source_stage_ids,
    build_stage_evidence_payload,
    build_stage_output_payload,
    compact_payload,
    find_stage,
    has_selected_idea,
    missing_experiment_setup_inputs,
    read_experiment_setup_inputs,
    read_selected_ideas,
    require_selected_idea_stage,
)
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

MAX_SELECTED_IDEAS_FOR_PROMPT = 3

__all__ = [
    "PLAN_ONLY_WARNING",
    "ExperimentPlannerRequest",
    "ExperimentPlannerStageRunner",
    "OpenAICompatibleExperimentPlannerRunner",
    "build_stage_output_payload",
    "has_selected_idea",
    "missing_experiment_setup_inputs",
    "parse_experiment_plan_output",
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


class ExperimentPlannerRunner(Protocol):
    def run(self, request: ExperimentPlannerRequest) -> ExperimentPlanOutput: ...


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
        "selected_ideas": request.selected_ideas[:MAX_SELECTED_IDEAS_FOR_PROMPT],
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


def get_experiment_planner_runner() -> ExperimentPlannerRunner:
    return OpenAICompatibleExperimentPlannerRunner()
