from typing import Literal

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator
from pydantic_core import PydanticCustomError

from noviscope.core.json_types import JsonObject
from noviscope.models.provider import ProviderKind

Confidence = Literal["high", "medium", "low"]
EvidenceType = Literal["paper_limitations", "metadata_inference", "human_context"]
Level = Literal["high", "medium", "low"]
SelectionStatus = Literal["pending_human_selection", "selected_for_experiment_design"]


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
            raise PydanticCustomError("empty_idea_id", "idea_id cannot be empty")
        return normalized


class GapHypothesisOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: str
    confidence: Confidence
    gaps: list[GapEvidence]
    ideas: list[HypothesisIdea]
    selected_idea_ids: list[str] = []
    selection_status: SelectionStatus
    source_stage_ids: JsonObject
    raw_response: str
    warnings: list[str] = []
