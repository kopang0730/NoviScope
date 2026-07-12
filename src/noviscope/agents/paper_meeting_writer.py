from dataclasses import dataclass
from typing import assert_never

from noviscope.agents.experiment_planner import read_selected_ideas
from noviscope.agents.gap_hypothesis import read_literature_papers
from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.agents.paper_meeting_contracts import (
    PaperMeetingWriterOutput,
    PaperMeetingWriterRequest,
    PaperMeetingWriterRunError,
    PaperMeetingWriterRunner,
)
from noviscope.agents.paper_meeting_payloads import (
    HUMAN_REVIEW_NOTICE,
    MAX_PAPERS_FOR_PROMPT,
    NO_RESULTS_NOTICE,
    build_stage_evidence_payload,
    build_stage_output_payload,
    compact_payload,
    parse_paper_meeting_writer_output,
)
from noviscope.agents.paper_meeting_prompt import build_chat_completion_payload
from noviscope.agents.provider_chat import (
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

__all__ = [
    "HUMAN_REVIEW_NOTICE",
    "NO_RESULTS_NOTICE",
    "OpenAICompatiblePaperMeetingWriterRunner",
    "PaperMeetingWriterOutput",
    "PaperMeetingWriterRequest",
    "PaperMeetingWriterRunError",
    "PaperMeetingWriterRunner",
    "PaperMeetingWriterStageRunner",
    "build_chat_completion_payload",
    "parse_paper_meeting_writer_output",
]


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
class PaperMeetingSourceStages:
    demand: StageCard | None
    literature: StageCard | None
    idea: StageCard | None
    experiment: StageCard | None


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
        source_stages = collect_source_stages(context.workflow_stages)
        return {
            "agent_id": context.stage.agent_id,
            "artifact_keys": [
                "chinese_research_brief_markdown",
                "english_research_brief_markdown",
                "meeting_outline_markdown",
                "ieee_paper_skeleton_markdown",
            ],
            "paper_count": len(read_literature_papers(source_stages.literature)),
            "provider_id": context.provider.id,
            "provider_model": context.provider.model,
            "provider_name": context.provider.name,
            "selected_idea_count": len(read_selected_ideas(source_stages.idea)),
            "source_stage_ids": build_source_stage_ids(source_stages),
        }

    def run(self, context: StageRunContext) -> StageRunResult:
        source_stages = collect_source_stages(context.workflow_stages)
        experiment_stage = require_complete_experiment_stage(source_stages)
        papers = read_literature_papers(source_stages.literature)
        selected_ideas = read_selected_ideas(source_stages.idea)
        source_stage_ids = build_source_stage_ids(source_stages)
        input_payload = self.build_input_payload(context)

        output = self.paper_runner.run(
            PaperMeetingWriterRequest(
                api_key=context.provider.api_key,
                base_url=context.provider.base_url,
                demand_validation=compact_payload(
                    source_stages.demand.output_payload if source_stages.demand is not None else {}
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


def find_stage(stages: tuple[StageCard, ...], agent_id: str) -> StageCard | None:
    return next((stage for stage in stages if stage.agent_id == agent_id), None)


def collect_source_stages(stages: tuple[StageCard, ...]) -> PaperMeetingSourceStages:
    return PaperMeetingSourceStages(
        demand=find_stage(stages, DEMAND_VALIDATOR_AGENT_ID),
        experiment=find_stage(stages, EXPERIMENT_PLANNER_AGENT_ID),
        idea=find_stage(stages, IDEA_GENERATOR_AGENT_ID),
        literature=find_stage(stages, LITERATURE_SCOUT_AGENT_ID),
    )


def require_complete_experiment_stage(source_stages: PaperMeetingSourceStages) -> StageCard:
    if source_stages.experiment is None or source_stages.experiment.status != StageStatus.COMPLETE:
        raise PaperMeetingWriterRunError(
            "Experiment Planner must complete before Paper & Meeting Writer runs."
        )
    return source_stages.experiment


def build_source_stage_ids(source_stages: PaperMeetingSourceStages) -> JsonObject:
    return {
        "demand_validation": source_stages.demand.id if source_stages.demand is not None else "",
        "experiment_planner": (
            source_stages.experiment.id if source_stages.experiment is not None else ""
        ),
        "idea_generator": source_stages.idea.id if source_stages.idea is not None else "",
        "literature_scout": (
            source_stages.literature.id if source_stages.literature is not None else ""
        ),
    }


def get_paper_meeting_writer_runner() -> PaperMeetingWriterRunner:
    return OpenAICompatiblePaperMeetingWriterRunner()
