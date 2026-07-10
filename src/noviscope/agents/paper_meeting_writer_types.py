from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from noviscope.core.json_types import JsonObject
from noviscope.models.provider import ProviderKind

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
    verified_experiment_results: list[JsonObject] = Field(default_factory=list)


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
    structured_response_valid: bool = Field(default=True, exclude=True)
    warnings: list[str] = []


class PaperMeetingWriterRunner(Protocol):
    def run(self, request: PaperMeetingWriterRequest) -> PaperMeetingWriterOutput: ...


@dataclass(frozen=True, slots=True)
class PaperMeetingWriterRunError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason
