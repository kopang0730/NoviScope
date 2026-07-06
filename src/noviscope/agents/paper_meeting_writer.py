import json
from dataclasses import dataclass
from typing import Literal, Protocol, assert_never

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError

from noviscope.agents.experiment_planner import read_selected_ideas
from noviscope.agents.gap_hypothesis import read_literature_papers
from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.agents.provider_chat import (
    ChatCompletionPayload,
    ProviderChatClient,
    ProviderChatRequest,
    ProviderChatRunError,
)
from noviscope.agents.stage_runner import StageRunContext, StageRunner, StageRunResult
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.models.provider import ProviderKind
from noviscope.models.quest import StageCard, StageStatus

MAX_TEXT_FIELD_CHARS = 900
MAX_PAPERS_FOR_PROMPT = 8
NO_RESULTS_NOTICE = (
    "No experiment results are available yet; result sections must stay as placeholders."
)
HUMAN_REVIEW_NOTICE = (
    "Human review is required before any draft can be used as a paper or meeting claim."
)

Confidence = Literal["high", "medium", "low"]


class PaperMeetingWriterRequest(BaseModel):
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
    selected_ideas: list[JsonObject]
    experiment_plan: JsonObject
    source_stage_ids: JsonObject


class PaperMeetingWriterOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: str
    confidence: Confidence
    chinese_research_brief_markdown: str
    english_research_brief_markdown: str
    meeting_outline_markdown: str
    ieee_paper_skeleton_markdown: str
    verified_facts: list[str]
    model_generated_hypotheses: list[str]
    experiment_results_not_available: list[str]
    human_review_required: list[str]
    source_stage_ids: JsonObject
    raw_response: str
    warnings: list[str] = []


class PaperMeetingWriterRunner(Protocol):
    def run(self, request: PaperMeetingWriterRequest) -> PaperMeetingWriterOutput: ...


@dataclass(frozen=True, slots=True)
class PaperMeetingWriterRunError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


class OpenAICompatiblePaperMeetingWriterRunner:
    def __init__(self, chat_client: ProviderChatClient | None = None) -> None:
        self._chat_client = chat_client or ProviderChatClient()

    def run(self, request: PaperMeetingWriterRequest) -> PaperMeetingWriterOutput:
        match request.provider_kind:
            case ProviderKind.OPENAI_COMPATIBLE | ProviderKind.CUSTOM | ProviderKind.ANTHROPIC:
                return self._run_provider_chat(request)
            case unreachable:
                assert_never(unreachable)

    def _run_provider_chat(
        self,
        request: PaperMeetingWriterRequest,
    ) -> PaperMeetingWriterOutput:
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
            raise PaperMeetingWriterRunError(str(exc)) from exc
        return parse_paper_meeting_writer_output(raw_content, request)


@dataclass(frozen=True, slots=True)
class PaperMeetingWriterStageRunner(StageRunner):
    paper_runner: PaperMeetingWriterRunner

    @property
    def agent_id(self) -> str:
        return PAPER_MEETING_WRITER_AGENT_ID

    @property
    def supported_provider_kinds(self) -> frozenset[ProviderKind]:
        return frozenset(
            {ProviderKind.ANTHROPIC, ProviderKind.OPENAI_COMPATIBLE, ProviderKind.CUSTOM}
        )

    def build_input_payload(self, context: StageRunContext) -> JsonObject:
        demand_stage = find_stage(context.workflow_stages, DEMAND_VALIDATOR_AGENT_ID)
        literature_stage = find_stage(context.workflow_stages, LITERATURE_SCOUT_AGENT_ID)
        idea_stage = find_stage(context.workflow_stages, IDEA_GENERATOR_AGENT_ID)
        experiment_stage = find_stage(context.workflow_stages, EXPERIMENT_PLANNER_AGENT_ID)
        return {
            "agent_id": context.stage.agent_id,
            "artifact_keys": [
                "chinese_research_brief_markdown",
                "english_research_brief_markdown",
                "meeting_outline_markdown",
                "ieee_paper_skeleton_markdown",
            ],
            "paper_count": len(read_literature_papers(literature_stage)),
            "provider_id": context.provider.id,
            "provider_model": context.provider.model,
            "provider_name": context.provider.name,
            "selected_idea_count": len(read_selected_ideas(idea_stage)),
            "source_stage_ids": build_source_stage_ids(
                demand_stage,
                literature_stage,
                idea_stage,
                experiment_stage,
            ),
        }

    def run(self, context: StageRunContext) -> StageRunResult:
        demand_stage = find_stage(context.workflow_stages, DEMAND_VALIDATOR_AGENT_ID)
        literature_stage = find_stage(context.workflow_stages, LITERATURE_SCOUT_AGENT_ID)
        idea_stage = find_stage(context.workflow_stages, IDEA_GENERATOR_AGENT_ID)
        experiment_stage = require_complete_experiment_stage(context.workflow_stages)
        papers = read_literature_papers(literature_stage)
        selected_ideas = read_selected_ideas(idea_stage)
        source_stage_ids = build_source_stage_ids(
            demand_stage,
            literature_stage,
            idea_stage,
            experiment_stage,
        )
        input_payload = self.build_input_payload(context)

        output = self.paper_runner.run(
            PaperMeetingWriterRequest(
                api_key=context.provider.api_key,
                base_url=context.provider.base_url,
                demand_validation=compact_payload(
                    demand_stage.output_payload if demand_stage is not None else {}
                ),
                experiment_plan=compact_payload(experiment_stage.output_payload),
                initial_direction=context.quest.initial_direction,
                model=context.provider.model,
                papers=papers[:MAX_PAPERS_FOR_PROMPT],
                provider_id=context.provider.id,
                provider_kind=context.provider.kind,
                provider_name=context.provider.name,
                quest_title=context.quest.title,
                selected_ideas=selected_ideas,
                source_stage_ids=source_stage_ids,
                stage_id=context.stage.id,
            )
        )

        return StageRunResult(
            confidence=output.confidence,
            evidence_payload=build_stage_evidence_payload(context, output),
            input_payload=input_payload,
            output_payload=build_stage_output_payload(output),
            summary=output.summary,
        )


def build_chat_completion_payload(request: PaperMeetingWriterRequest) -> ChatCompletionPayload:
    prompt_payload = {
        "demand_validation": compact_payload(request.demand_validation),
        "experiment_plan": compact_payload(request.experiment_plan),
        "papers": request.papers[:MAX_PAPERS_FOR_PROMPT],
        "quest": {
            "initial_direction": request.initial_direction,
            "title": request.quest_title,
        },
        "selected_ideas": request.selected_ideas,
        "source_stage_ids": request.source_stage_ids,
    }
    return {
        "messages": [
            {
                "content": (
                    "You are NoviScope's Paper & Meeting Writer. Return only valid JSON with "
                    "keys summary, confidence, chinese_research_brief_markdown, "
                    "english_research_brief_markdown, meeting_outline_markdown, "
                    "ieee_paper_skeleton_markdown, verified_facts, "
                    "model_generated_hypotheses, experiment_results_not_available, "
                    "human_review_required, warnings. Use Markdown strings for the four "
                    "artifacts. Clearly separate verified facts from generated hypotheses. "
                    "Do not invent citations, metric values, benchmark scores, or completed "
                    "experiments. The IEEE skeleton must keep Results and Conclusion sections "
                    "as placeholders because experiments have not run. Every claim that needs "
                    "review must appear in human_review_required."
                ),
                "role": "system",
            },
            {
                "content": json.dumps(prompt_payload, ensure_ascii=False),
                "role": "user",
            },
        ],
        "model": request.model,
        "temperature": 0.25,
    }


def parse_paper_meeting_writer_output(
    raw_content: str,
    request: PaperMeetingWriterRequest,
) -> PaperMeetingWriterOutput:
    try:
        parsed_content = json.loads(raw_content)
        output = PaperMeetingWriterOutput.model_validate(
            {
                **parsed_content,
                "raw_response": raw_content,
                "source_stage_ids": request.source_stage_ids,
            }
        )
    except (json.JSONDecodeError, TypeError, ValidationError):
        return PaperMeetingWriterOutput(
            chinese_research_brief_markdown="",
            confidence="low",
            english_research_brief_markdown="",
            experiment_results_not_available=[NO_RESULTS_NOTICE],
            human_review_required=[HUMAN_REVIEW_NOTICE],
            ieee_paper_skeleton_markdown="",
            meeting_outline_markdown="",
            model_generated_hypotheses=[],
            raw_response=raw_content,
            source_stage_ids=request.source_stage_ids,
            summary="The model response was not valid structured JSON.",
            verified_facts=[],
            warnings=["The model response was not valid structured JSON."],
        )
    return constrain_output(output)


def constrain_output(output: PaperMeetingWriterOutput) -> PaperMeetingWriterOutput:
    warnings = list(output.warnings)
    experiment_results_not_available = list(output.experiment_results_not_available)
    human_review_required = list(output.human_review_required)
    if NO_RESULTS_NOTICE not in experiment_results_not_available:
        experiment_results_not_available.append(NO_RESULTS_NOTICE)
    if HUMAN_REVIEW_NOTICE not in human_review_required:
        human_review_required.append(HUMAN_REVIEW_NOTICE)
    return output.model_copy(
        update={
            "confidence": cap_confidence(output.confidence),
            "experiment_results_not_available": experiment_results_not_available,
            "human_review_required": human_review_required,
            "warnings": warnings,
        }
    )


def cap_confidence(confidence: str) -> Confidence:
    if confidence == "high":
        return "medium"
    if confidence == "medium":
        return "medium"
    return "low"


def build_stage_output_payload(output: PaperMeetingWriterOutput) -> JsonObject:
    return {
        "chinese_research_brief_markdown": output.chinese_research_brief_markdown,
        "confidence": output.confidence,
        "english_research_brief_markdown": output.english_research_brief_markdown,
        "experiment_results_not_available": output.experiment_results_not_available,
        "human_review_required": output.human_review_required,
        "ieee_paper_skeleton_markdown": output.ieee_paper_skeleton_markdown,
        "meeting_outline_markdown": output.meeting_outline_markdown,
        "model_generated_hypotheses": output.model_generated_hypotheses,
        "raw_response": output.raw_response,
        "source_stage_ids": output.source_stage_ids,
        "summary": output.summary,
        "verified_facts": output.verified_facts,
        "warnings": output.warnings,
    }


def build_stage_evidence_payload(
    context: StageRunContext,
    output: PaperMeetingWriterOutput,
) -> JsonObject:
    return {
        "artifact_count": 4,
        "can_run": True,
        "download_format": "markdown",
        "no_experiment_results": True,
        "provider_id": context.provider.id,
        "provider_model": context.provider.model,
        "provider_name": context.provider.name,
        "requires_human_review": True,
        "source_stage_ids": output.source_stage_ids,
        "warning_count": len(output.warnings),
    }


def find_stage(stages: tuple[StageCard, ...], agent_id: str) -> StageCard | None:
    return next((stage for stage in stages if stage.agent_id == agent_id), None)


def require_complete_experiment_stage(stages: tuple[StageCard, ...]) -> StageCard:
    stage = find_stage(stages, EXPERIMENT_PLANNER_AGENT_ID)
    if stage is None or stage.status != StageStatus.COMPLETE:
        raise PaperMeetingWriterRunError(
            "Experiment Planner must complete before Paper & Meeting Writer runs."
        )
    return stage


def build_source_stage_ids(
    demand_stage: StageCard | None,
    literature_stage: StageCard | None,
    idea_stage: StageCard | None,
    experiment_stage: StageCard | None,
) -> JsonObject:
    return {
        "demand_validation": demand_stage.id if demand_stage is not None else "",
        "experiment_planner": experiment_stage.id if experiment_stage is not None else "",
        "idea_generator": idea_stage.id if idea_stage is not None else "",
        "literature_scout": literature_stage.id if literature_stage is not None else "",
    }


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
                for item in value[:10]
                if isinstance(item, str | int | float | bool | dict)
            ]
        elif isinstance(value, int | float | bool | dict) or value is None:
            compacted[key] = value
    return compacted


def trim_text(value: str) -> str:
    return " ".join(value.split())[:MAX_TEXT_FIELD_CHARS]


def get_paper_meeting_writer_runner() -> PaperMeetingWriterRunner:
    return OpenAICompatiblePaperMeetingWriterRunner()
