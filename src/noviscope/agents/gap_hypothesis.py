import json
from dataclasses import dataclass
from typing import Protocol, assert_never

from noviscope.agents.gap_hypothesis_contracts import (
    GapEvidence,
    GapHypothesisOutput,
    GapHypothesisRequest,
    HypothesisIdea,
)
from noviscope.agents.gap_hypothesis_outputs import (
    build_no_paper_output,
    build_stage_output_payload,
    parse_gap_hypothesis_output,
)
from noviscope.agents.gap_hypothesis_payloads import (
    MAX_PAPERS_FOR_PROMPT,
    compact_payload,
    read_literature_papers,
)
from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.agents.provider_chat import (
    ChatCompletionPayload,
    ProviderChatClient,
    ProviderChatRequest,
    ProviderChatRunError,
)
from noviscope.agents.stage_runner import StageRunContext, StageRunner, StageRunResult
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import DEMAND_VALIDATOR_AGENT_ID, IDEA_GENERATOR_AGENT_ID
from noviscope.models.provider import ProviderKind
from noviscope.models.quest import StageCard, StageStatus

__all__ = [
    "GapEvidence",
    "GapHypothesisOutput",
    "GapHypothesisRequest",
    "GapHypothesisRunError",
    "GapHypothesisRunner",
    "GapHypothesisStageRunner",
    "HypothesisIdea",
    "OpenAICompatibleGapHypothesisRunner",
    "build_no_paper_output",
    "build_stage_output_payload",
    "get_gap_hypothesis_runner",
    "parse_gap_hypothesis_output",
    "read_literature_papers",
]


class GapHypothesisRunner(Protocol):
    def run(self, request: GapHypothesisRequest) -> GapHypothesisOutput: ...


@dataclass(frozen=True, slots=True)
class GapHypothesisRunError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


class OpenAICompatibleGapHypothesisRunner:
    def __init__(self, chat_client: ProviderChatClient | None = None) -> None:
        self._chat_client = chat_client or ProviderChatClient()

    def run(self, request: GapHypothesisRequest) -> GapHypothesisOutput:
        match request.provider_kind:
            case ProviderKind.OPENAI_COMPATIBLE | ProviderKind.CUSTOM | ProviderKind.ANTHROPIC:
                return self._run_provider_chat(request)
            case unreachable:
                assert_never(unreachable)

    def _run_provider_chat(self, request: GapHypothesisRequest) -> GapHypothesisOutput:
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
            raise GapHypothesisRunError(str(exc)) from exc
        return parse_gap_hypothesis_output(raw_content, request)


@dataclass(frozen=True, slots=True)
class GapHypothesisStageRunner(StageRunner):
    gap_runner: GapHypothesisRunner

    @property
    def agent_id(self) -> str:
        return IDEA_GENERATOR_AGENT_ID

    @property
    def supported_provider_kinds(self) -> frozenset[ProviderKind]:
        return frozenset(
            {ProviderKind.ANTHROPIC, ProviderKind.OPENAI_COMPATIBLE, ProviderKind.CUSTOM}
        )

    def build_input_payload(self, context: StageRunContext) -> JsonObject:
        demand_stage = find_stage(context.workflow_stages, DEMAND_VALIDATOR_AGENT_ID)
        literature_stage = find_stage(context.workflow_stages, LITERATURE_SCOUT_AGENT_ID)
        papers = read_literature_papers(literature_stage)
        return {
            "agent_id": context.stage.agent_id,
            "paper_count": len(papers),
            "provider_id": context.provider.id,
            "provider_model": context.provider.model,
            "provider_name": context.provider.name,
            "source_stage_ids": build_source_stage_ids(demand_stage, literature_stage),
        }

    def run(self, context: StageRunContext) -> StageRunResult:
        demand_stage = require_complete_stage(context.workflow_stages, DEMAND_VALIDATOR_AGENT_ID)
        literature_stage = require_complete_stage(
            context.workflow_stages,
            LITERATURE_SCOUT_AGENT_ID,
        )
        papers = read_literature_papers(literature_stage)
        source_stage_ids = build_source_stage_ids(demand_stage, literature_stage)
        input_payload = self.build_input_payload(context)

        if not papers:
            output = build_no_paper_output(source_stage_ids)
        else:
            output = self.gap_runner.run(
                GapHypothesisRequest(
                    api_key=context.provider.api_key,
                    base_url=context.provider.base_url,
                    demand_validation=demand_stage.output_payload,
                    initial_direction=context.quest.initial_direction,
                    model=context.provider.model,
                    papers=papers,
                    provider_id=context.provider.id,
                    provider_kind=context.provider.kind,
                    provider_name=context.provider.name,
                    quest_title=context.quest.title,
                    source_stage_ids=source_stage_ids,
                    stage_id=context.stage.id,
                )
            )

        return StageRunResult(
            confidence=output.confidence,
            evidence_payload=build_stage_evidence_payload(context, output, papers),
            input_payload=input_payload,
            output_payload=build_stage_output_payload(output),
            summary=output.summary,
        )


def build_chat_completion_payload(request: GapHypothesisRequest) -> ChatCompletionPayload:
    prompt_payload = {
        "demand_validation": compact_payload(request.demand_validation),
        "papers": request.papers[:MAX_PAPERS_FOR_PROMPT],
        "quest": {
            "initial_direction": request.initial_direction,
            "title": request.quest_title,
        },
        "source_stage_ids": request.source_stage_ids,
    }
    return {
        "messages": [
            {
                "content": (
                    "You are NoviScope's Gap & Hypothesis Generator. Return only valid JSON "
                    "with keys summary, confidence, gaps, ideas. Use only the provided papers "
                    "as literature evidence. Do not invent citations, benchmark scores, "
                    "datasets, experiment results, or claims of validation. Each idea must "
                    "include idea_id, idea_title, core_hypothesis, based_on_which_papers, "
                    "expected_improvement, required_data, required_baseline, "
                    "experiment_feasibility, novelty_risk, application_value, confidence. "
                    "Confidence values are high, medium, or low, but keep hypotheses cautious "
                    "because no experiment has run. based_on_which_papers and gap "
                    "supporting_papers must use exact paper_ref values from the provided "
                    "papers."
                ),
                "role": "system",
            },
            {
                "content": json.dumps(prompt_payload, ensure_ascii=False),
                "role": "user",
            },
        ],
        "model": request.model,
        "temperature": 0.3,
    }


def build_stage_evidence_payload(
    context: StageRunContext,
    output: GapHypothesisOutput,
    papers: list[JsonObject],
) -> JsonObject:
    return {
        "can_run": True,
        "idea_count": len(output.ideas),
        "paper_count": len(papers),
        "provider_id": context.provider.id,
        "provider_model": context.provider.model,
        "provider_name": context.provider.name,
        "requires_human_review": True,
        "source_stage_ids": output.source_stage_ids,
        "warning_count": len(output.warnings),
    }


def find_stage(stages: tuple[StageCard, ...], agent_id: str) -> StageCard | None:
    return next((stage for stage in stages if stage.agent_id == agent_id), None)


def require_complete_stage(stages: tuple[StageCard, ...], agent_id: str) -> StageCard:
    stage = find_stage(stages, agent_id)
    if stage is None or stage.status != StageStatus.COMPLETE:
        raise GapHypothesisRunError(f"{agent_id} must complete before Gap/Hypothesis runs.")
    return stage


def build_source_stage_ids(
    demand_stage: StageCard | None,
    literature_stage: StageCard | None,
) -> JsonObject:
    return {
        "demand_validation": demand_stage.id if demand_stage is not None else "",
        "literature_scout": literature_stage.id if literature_stage is not None else "",
    }


def get_gap_hypothesis_runner() -> GapHypothesisRunner:
    return OpenAICompatibleGapHypothesisRunner()
