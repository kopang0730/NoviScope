import json
from dataclasses import dataclass
from typing import Literal, Protocol, assert_never

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError, field_validator

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
from noviscope.models.provider import ProviderApiMode, ProviderKind
from noviscope.models.quest import StageCard, StageStatus

MAX_PAPERS_FOR_PROMPT = 8
MAX_TEXT_FIELD_CHARS = 500

Confidence = Literal["high", "medium", "low"]
EvidenceType = Literal["paper_limitations", "metadata_inference", "human_context"]
Level = Literal["high", "medium", "low"]


class GapHypothesisRequest(BaseModel):
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
    demand_validation: JsonObject
    papers: list[JsonObject]
    source_stage_ids: JsonObject
    api_mode: ProviderApiMode = ProviderApiMode.AUTO


class GapEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    gap_title: str
    description: str
    supporting_papers: list[str]
    severity: Level
    evidence_type: EvidenceType


class HypothesisIdea(BaseModel):
    model_config = ConfigDict(frozen=True)

    idea_id: str
    idea_title: str
    core_hypothesis: str
    based_on_which_papers: list[str]
    expected_improvement: str
    required_data: str
    required_baseline: str
    experiment_feasibility: Level
    novelty_risk: Level
    application_value: Level
    confidence: Confidence

    @field_validator("idea_id")
    @classmethod
    def validate_idea_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("idea_id cannot be empty")
        return normalized


class GapHypothesisOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: str
    confidence: Confidence
    gaps: list[GapEvidence]
    ideas: list[HypothesisIdea]
    selected_idea_ids: list[str] = []
    selection_status: Literal["pending_human_selection", "selected_for_experiment_design"]
    source_stage_ids: JsonObject
    raw_response: str
    warnings: list[str] = []


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
                    api_mode=request.api_mode,
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
                    api_mode=context.provider.api_mode,
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
                    "because no experiment has run. based_on_which_papers must use exact "
                    "paper_ref values from the provided papers."
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


def parse_gap_hypothesis_output(
    raw_content: str,
    request: GapHypothesisRequest,
) -> GapHypothesisOutput:
    try:
        parsed_content = json.loads(raw_content)
        output = GapHypothesisOutput.model_validate(
            {
                **parsed_content,
                "raw_response": raw_content,
                "selected_idea_ids": [],
                "selection_status": "pending_human_selection",
                "source_stage_ids": request.source_stage_ids,
            }
        )
    except (json.JSONDecodeError, TypeError, ValidationError):
        return GapHypothesisOutput(
            confidence="low",
            gaps=[],
            ideas=[],
            raw_response=raw_content,
            selected_idea_ids=[],
            selection_status="pending_human_selection",
            source_stage_ids=request.source_stage_ids,
            summary="The model response was not valid structured JSON.",
            warnings=["The model response was not valid structured JSON."],
        )
    return constrain_output_to_known_papers(output, request.papers)


def constrain_output_to_known_papers(
    output: GapHypothesisOutput,
    papers: list[JsonObject],
) -> GapHypothesisOutput:
    known_refs = known_paper_refs(papers)
    warnings = list(output.warnings)
    ideas: list[HypothesisIdea] = []
    for idea in output.ideas:
        valid_refs = [ref for ref in idea.based_on_which_papers if ref in known_refs]
        if len(valid_refs) != len(idea.based_on_which_papers):
            warnings.append(
                f"Removed unrecognized paper references from {idea.idea_id}; verify citations."
            )
        confidence = cap_confidence(idea.confidence)
        if not valid_refs:
            confidence = "low"
            warnings.append(f"{idea.idea_id} has no recognized paper reference.")
        ideas.append(
            idea.model_copy(
                update={
                    "based_on_which_papers": valid_refs,
                    "confidence": confidence,
                }
            )
        )

    gaps = [
        gap.model_copy(
            update={
                "supporting_papers": [
                    ref for ref in gap.supporting_papers if ref in known_refs
                ],
            }
        )
        for gap in output.gaps
    ]

    return output.model_copy(
        update={
            "confidence": cap_confidence(output.confidence),
            "gaps": gaps,
            "ideas": ideas,
            "warnings": warnings,
        }
    )


def cap_confidence(confidence: str) -> Confidence:
    if confidence == "high":
        return "medium"
    if confidence == "medium":
        return "medium"
    return "low"


def build_no_paper_output(source_stage_ids: JsonObject) -> GapHypothesisOutput:
    return GapHypothesisOutput(
        confidence="low",
        gaps=[],
        ideas=[],
        raw_response="",
        selected_idea_ids=[],
        selection_status="pending_human_selection",
        source_stage_ids=source_stage_ids,
        summary="No hypotheses generated because Literature Scout returned no papers.",
        warnings=["Literature Scout returned no papers; NoviScope did not fabricate ideas."],
    )


def build_stage_output_payload(output: GapHypothesisOutput) -> JsonObject:
    return {
        "confidence": output.confidence,
        "gaps": [gap.model_dump() for gap in output.gaps],
        "ideas": [idea.model_dump() for idea in output.ideas],
        "raw_response": output.raw_response,
        "selected_idea_ids": output.selected_idea_ids,
        "selection_status": output.selection_status,
        "source_stage_ids": output.source_stage_ids,
        "summary": output.summary,
        "warnings": output.warnings,
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


def read_literature_papers(stage: StageCard | None) -> list[JsonObject]:
    if stage is None:
        return []
    paper_values = stage.output_payload.get("papers")
    if not isinstance(paper_values, list):
        return []
    papers: list[JsonObject] = []
    for value in paper_values[:MAX_PAPERS_FOR_PROMPT]:
        if isinstance(value, dict):
            paper = normalize_paper_payload(value)
            if paper is not None:
                papers.append(paper)
    return papers


def normalize_paper_payload(value: dict[object, object]) -> JsonObject | None:
    title = string_value(value.get("title"))
    paper_ref = first_present_string(
        value.get("openalex_id"),
        value.get("doi"),
        value.get("url"),
        title,
    )
    if not paper_ref:
        return None
    return {
        "abstract_summary": trim_text(string_value(value.get("abstract_summary"))),
        "limitations": string_list(value.get("limitations")),
        "paper_ref": paper_ref,
        "relevance_score": number_value(value.get("relevance_score")),
        "reliability_level": string_value(value.get("reliability_level")),
        "title": title or paper_ref,
        "venue": string_value(value.get("venue")),
        "why_relevant": trim_text(string_value(value.get("why_relevant"))),
        "year": value.get("year") if isinstance(value.get("year"), int) else None,
    }


def known_paper_refs(papers: list[JsonObject]) -> set[str]:
    refs: set[str] = set()
    for paper in papers:
        for key in ("paper_ref", "title"):
            value = paper.get(key)
            if isinstance(value, str) and value:
                refs.add(value)
    return refs


def compact_payload(payload: JsonObject) -> JsonObject:
    compacted: JsonObject = {}
    for key, value in payload.items():
        if key == "raw_response":
            continue
        if isinstance(value, str):
            compacted[key] = trim_text(value)
        elif isinstance(value, list):
            compacted[key] = [
                trim_text(item) if isinstance(item, str) else item
                for item in value[:8]
                if isinstance(item, str | int | float | bool | dict)
            ]
        elif isinstance(value, int | float | bool | dict) or value is None:
            compacted[key] = value
    return compacted


def trim_text(value: str) -> str:
    return " ".join(value.split())[:MAX_TEXT_FIELD_CHARS]


def string_value(value: object) -> str:
    return value if isinstance(value, str) else ""


def first_present_string(*values: object) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""


def string_list(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def number_value(value: object) -> float:
    return float(value) if isinstance(value, int | float) else 0.0


def get_gap_hypothesis_runner() -> GapHypothesisRunner:
    return OpenAICompatibleGapHypothesisRunner()
