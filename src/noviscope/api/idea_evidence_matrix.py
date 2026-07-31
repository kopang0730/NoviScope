from dataclasses import dataclass
from typing import Annotated, ClassVar, Final

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.api.dependencies import get_session
from noviscope.api.idea_selection import idea_payloads
from noviscope.api.literature_paper_table import (
    LiteraturePaperRow,
    paper_row,
    read_paper_payloads,
    read_string_list,
    read_text,
)
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import IDEA_GENERATOR_AGENT_ID
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

INCOMPLETE_STAGE_REASON: Final = (
    "Gap & hypothesis generator must complete before idea evidence is available."
)
WRONG_STAGE_REASON: Final = "This stage does not expose Gap & hypothesis ideas."


class IdeaEvidencePaperResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    paper_ref: str
    relevance_score: float
    reliability_level: str
    title: str
    venue: str
    why_relevant: str
    year: int | None


class IdeaEvidenceRowResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    application_value: str
    confidence: str
    core_hypothesis: str
    expected_improvement: str
    experiment_feasibility: str
    idea_id: str
    idea_title: str
    linked_papers: list[IdeaEvidencePaperResponse]
    missing_source_refs: list[str]
    novelty_risk: str
    recognized_source_count: int
    required_baseline: str
    required_data: str
    source_paper_refs: list[str]


class IdeaEvidenceMatrixResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    idea_count: int
    ideas: list[IdeaEvidenceRowResponse]
    requires_human_selection: bool
    selected_idea_ids: list[str]
    selection_status: str
    source_stage_ids: dict[str, str]
    stage_id: str
    unavailable_reason: str


@dataclass(frozen=True, slots=True)
class IdeaEvidenceMatrixContext:
    session: Session
    current_user: User


def get_idea_evidence_matrix_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IdeaEvidenceMatrixContext:
    return IdeaEvidenceMatrixContext(current_user=current_user, session=session)


def paper_response(row: LiteraturePaperRow) -> IdeaEvidencePaperResponse:
    return IdeaEvidencePaperResponse(
        paper_ref=row.paper_ref,
        relevance_score=row.relevance_score,
        reliability_level=row.reliability_level,
        title=row.title,
        venue=row.venue,
        why_relevant=row.why_relevant,
        year=row.year,
    )


def paper_lookup(stage: StageCard | None) -> dict[str, IdeaEvidencePaperResponse]:
    if stage is None or stage.status != StageStatus.COMPLETE:
        return {}
    lookup: dict[str, IdeaEvidencePaperResponse] = {}
    for payload in read_paper_payloads(stage.output_payload):
        row = paper_row(payload)
        response = paper_response(row)
        if response.paper_ref:
            lookup[response.paper_ref] = response
        if response.title:
            lookup[response.title] = response
    return lookup


def source_stage_ids(payload: JsonObject) -> dict[str, str]:
    value = payload.get("source_stage_ids")
    if not isinstance(value, dict):
        return {}
    return {
        key: item
        for key, item in value.items()
        if isinstance(key, str) and isinstance(item, str)
    }


def empty_response(
    stage: StageCard,
    source_ids: dict[str, str],
    unavailable_reason: str,
) -> IdeaEvidenceMatrixResponse:
    return IdeaEvidenceMatrixResponse(
        idea_count=0,
        ideas=[],
        requires_human_selection=True,
        selected_idea_ids=[],
        selection_status="",
        source_stage_ids=source_ids,
        stage_id=stage.id,
        unavailable_reason=unavailable_reason,
    )


def linked_papers_for_refs(
    refs: list[str],
    papers_by_ref: dict[str, IdeaEvidencePaperResponse],
) -> list[IdeaEvidencePaperResponse]:
    papers: list[IdeaEvidencePaperResponse] = []
    seen: set[str] = set()
    for ref in refs:
        paper = papers_by_ref.get(ref)
        if paper is None or paper.paper_ref in seen:
            continue
        seen.add(paper.paper_ref)
        papers.append(paper)
    return papers


def idea_row(
    idea: JsonObject,
    papers_by_ref: dict[str, IdeaEvidencePaperResponse],
) -> IdeaEvidenceRowResponse:
    refs = read_string_list(idea, "based_on_which_papers")
    linked_papers = linked_papers_for_refs(refs, papers_by_ref)
    recognized_refs = {paper.paper_ref for paper in linked_papers}
    return IdeaEvidenceRowResponse(
        application_value=read_text(idea, "application_value"),
        confidence=read_text(idea, "confidence"),
        core_hypothesis=read_text(idea, "core_hypothesis"),
        expected_improvement=read_text(idea, "expected_improvement"),
        experiment_feasibility=read_text(idea, "experiment_feasibility"),
        idea_id=read_text(idea, "idea_id"),
        idea_title=read_text(idea, "idea_title"),
        linked_papers=linked_papers,
        missing_source_refs=[
            ref for ref in refs if ref not in papers_by_ref and ref not in recognized_refs
        ],
        novelty_risk=read_text(idea, "novelty_risk"),
        recognized_source_count=len(linked_papers),
        required_baseline=read_text(idea, "required_baseline"),
        required_data=read_text(idea, "required_data"),
        source_paper_refs=refs,
    )


def find_literature_stage(stages: list[StageCard]) -> StageCard | None:
    return next((stage for stage in stages if stage.agent_id == LITERATURE_SCOUT_AGENT_ID), None)


def build_idea_evidence_matrix(
    stage: StageCard,
    quest_stages: list[StageCard],
) -> IdeaEvidenceMatrixResponse:
    source_ids = source_stage_ids(stage.output_payload)
    if stage.agent_id != IDEA_GENERATOR_AGENT_ID:
        return empty_response(stage, source_ids, WRONG_STAGE_REASON)
    if stage.status != StageStatus.COMPLETE:
        return empty_response(stage, source_ids, INCOMPLETE_STAGE_REASON)

    papers_by_ref = paper_lookup(find_literature_stage(quest_stages))
    ideas = [idea_row(idea, papers_by_ref) for idea in idea_payloads(stage.output_payload)]
    selection_status = read_text(stage.output_payload, "selection_status")
    return IdeaEvidenceMatrixResponse(
        idea_count=len(ideas),
        ideas=ideas,
        requires_human_selection=selection_status != "selected_for_experiment_design",
        selected_idea_ids=read_string_list(stage.output_payload, "selected_idea_ids"),
        selection_status=selection_status,
        source_stage_ids=source_ids,
        stage_id=stage.id,
        unavailable_reason="",
    )


@router.get("/stages/{stage_id}/idea-evidence-matrix", response_model=IdeaEvidenceMatrixResponse)
def get_idea_evidence_matrix(
    stage_id: str,
    context: Annotated[
        IdeaEvidenceMatrixContext,
        Depends(get_idea_evidence_matrix_context),
    ],
) -> IdeaEvidenceMatrixResponse:
    service = QuestService(context.session)
    try:
        stage = service.get_stage_card_for_user(stage_id, context.current_user)
        quest_stages = service.list_stage_cards(stage.quest_id)
        return build_idea_evidence_matrix(stage, quest_stages)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
