import json
from dataclasses import dataclass
from typing import Literal, Protocol, assert_never

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError

from noviscope.agents.provider_chat import (
    ChatCompletionPayload,
    ProviderChatClient,
    ProviderChatRequest,
    ProviderChatRunError,
)
from noviscope.agents.stage_runner import StageRunContext, StageRunner, StageRunResult
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import DEMAND_VALIDATOR_AGENT_ID, NO_EXTERNAL_VERIFICATION_RISK
from noviscope.models.provider import ProviderKind


class DemandValidationRequest(BaseModel):
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


class DemandValidationOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: str
    demand_assessment: Literal["strong", "plausible", "weak", "unclear"]
    confidence: Literal["high", "medium", "low"]
    evidence: list[str] = []
    evidence_for_demand: list[str]
    go_or_no_go_recommendation: Literal[
        "go",
        "go_with_human_review",
        "needs_more_evidence",
        "no_go",
    ]
    missing_evidence: list[str]
    risks: list[str]
    real_world_scenario: str
    target_user_or_customer: str
    suggested_human_checklist: list[str]
    next_step: str
    raw_response: str


class DemandValidationRunner(Protocol):
    def run(self, request: DemandValidationRequest) -> DemandValidationOutput: ...


@dataclass(frozen=True, slots=True)
class DemandValidationRunError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


class OpenAICompatibleDemandValidationRunner:
    def __init__(self, chat_client: ProviderChatClient | None = None) -> None:
        self._chat_client = chat_client or ProviderChatClient()

    def run(self, request: DemandValidationRequest) -> DemandValidationOutput:
        match request.provider_kind:
            case ProviderKind.OPENAI_COMPATIBLE | ProviderKind.CUSTOM | ProviderKind.ANTHROPIC:
                return self._run_provider_chat(request)
            case unreachable:
                assert_never(unreachable)

    def _run_provider_chat(self, request: DemandValidationRequest) -> DemandValidationOutput:
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
            raise DemandValidationRunError(str(exc)) from exc
        return parse_demand_validation_output(raw_content)


@dataclass(frozen=True, slots=True)
class DemandValidationStageRunner(StageRunner):
    demand_runner: DemandValidationRunner

    @property
    def agent_id(self) -> str:
        return DEMAND_VALIDATOR_AGENT_ID

    @property
    def supported_provider_kinds(self) -> frozenset[ProviderKind]:
        return frozenset(
            {ProviderKind.ANTHROPIC, ProviderKind.OPENAI_COMPATIBLE, ProviderKind.CUSTOM}
        )

    def build_input_payload(self, context: StageRunContext) -> JsonObject:
        return {
            "agent_id": context.stage.agent_id,
            "provider_id": context.provider.id,
            "provider_name": context.provider.name,
            "provider_model": context.provider.model,
        }

    def run(self, context: StageRunContext) -> StageRunResult:
        output = self.demand_runner.run(
            DemandValidationRequest(
                api_key=context.provider.api_key,
                base_url=context.provider.base_url,
                initial_direction=context.quest.initial_direction,
                model=context.provider.model,
                provider_id=context.provider.id,
                provider_kind=context.provider.kind,
                provider_name=context.provider.name,
                quest_title=context.quest.title,
                stage_id=context.stage.id,
            )
        )
        input_payload = self.build_input_payload(context)
        return StageRunResult(
            confidence=output.confidence,
            evidence_payload=build_stage_evidence_payload(context, output),
            input_payload=input_payload,
            output_payload=build_stage_output_payload(output),
            summary=output.summary,
        )


def build_chat_completion_payload(request: DemandValidationRequest) -> ChatCompletionPayload:
    return {
        "messages": [
            {
                "content": (
                    "You are NoviScope's Demand Validator. Return only valid JSON with keys "
                    "summary, demand_assessment, confidence, real_world_scenario, "
                    "target_user_or_customer, evidence_for_demand, missing_evidence, risks, "
                    "suggested_human_checklist, go_or_no_go_recommendation, next_step. "
                    "demand_assessment must be one of strong, plausible, weak, unclear. "
                    "Treat user-provided demand evidence sources as unverified leads: use them "
                    "to shape evidence_for_demand, missing_evidence, and the human checklist, "
                    "but do not treat them as confirmed proof. "
                    "confidence must be one of high, medium, low. Because this MVP has not "
                    "performed external source verification, do not return high confidence."
                ),
                "role": "system",
            },
            {
                "content": (
                    f"Quest title: {request.quest_title}\n\n"
                    f"Initial research direction:\n{request.initial_direction}\n\n"
                    "Judge whether this is a real demand, identify weak evidence, and propose "
                    "the next human-review step before experiments. Do not invent enterprise "
                    "evidence, customer evidence, or experiment results."
                ),
                "role": "user",
            },
        ],
        "model": request.model,
        "temperature": 0.2,
    }


def parse_demand_validation_output(raw_content: str) -> DemandValidationOutput:
    try:
        parsed_content = json.loads(raw_content)
        output = DemandValidationOutput.model_validate(
            {**parsed_content, "raw_response": raw_content}
        )
        if output.confidence == "high":
            risks = output.risks
            if NO_EXTERNAL_VERIFICATION_RISK not in risks:
                risks = [*risks, NO_EXTERNAL_VERIFICATION_RISK]
            return output.model_copy(
                update={
                    "confidence": "medium",
                    "risks": risks,
                }
            )
        return output
    except (json.JSONDecodeError, TypeError, ValidationError):
        return DemandValidationOutput(
            confidence="low",
            demand_assessment="unclear",
            evidence=[],
            evidence_for_demand=[],
            go_or_no_go_recommendation="needs_more_evidence",
            missing_evidence=["The model response was not valid structured JSON."],
            next_step="Ask a human reviewer to inspect the raw model response.",
            raw_response=raw_content,
            real_world_scenario="",
            risks=["The model response was not valid structured JSON."],
            summary=raw_content[:240] or "Model returned an empty response.",
            suggested_human_checklist=["Review the raw response and rerun the stage."],
            target_user_or_customer="",
        )


def build_stage_output_payload(output: DemandValidationOutput) -> JsonObject:
    return {
        "confidence": output.confidence,
        "demand_assessment": output.demand_assessment,
        "evidence": output.evidence,
        "evidence_for_demand": output.evidence_for_demand,
        "go_or_no_go_recommendation": output.go_or_no_go_recommendation,
        "missing_evidence": output.missing_evidence,
        "next_step": output.next_step,
        "raw_response": output.raw_response,
        "real_world_scenario": output.real_world_scenario,
        "risks": output.risks,
        "suggested_human_checklist": output.suggested_human_checklist,
        "target_user_or_customer": output.target_user_or_customer,
    }


def build_stage_evidence_payload(
    context: StageRunContext,
    output: DemandValidationOutput,
) -> JsonObject:
    return {
        "can_run": True,
        "provider_id": context.provider.id,
        "provider_name": context.provider.name,
        "provider_model": context.provider.model,
        "risk_count": len(output.risks),
        "requires_human_review": True,
        "source_policy": "model_only_no_external_source_verification",
    }


def get_demand_validation_runner() -> DemandValidationRunner:
    return OpenAICompatibleDemandValidationRunner()
