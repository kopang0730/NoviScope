from dataclasses import dataclass
from typing import Final, assert_never

from pydantic import BaseModel, ConfigDict

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.api.literature_paper_table import (
    LiteraturePaperRow,
    paper_ref,
    paper_row,
    read_paper_payloads,
    read_text,
)
from noviscope.models.quest import StageCard, StageStatus

INCOMPLETE_DETAIL_REASON: Final = (
    "Literature Scout must complete before paper details are available."
)
WRONG_STAGE_DETAIL_REASON: Final = "This stage does not expose Literature Scout paper details."
VERIFY_METADATA_WARNING: Final = (
    "Verify the URL, DOI, venue, and year against the publisher or index page."
)
OPENALEX_METADATA_WARNING: Final = (
    "Treat OpenAlex metadata as retrieval evidence, not as a full-paper review."
)


@dataclass(frozen=True, slots=True)
class LiteraturePaperNotFoundError(Exception):
    stage_id: str
    paper_ref: str

    def __str__(self) -> str:
        return f"Paper reference {self.paper_ref!r} was not found in stage {self.stage_id}."


class LiteraturePaperDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_id: str
    paper_ref: str
    source: str
    search_query: str
    score_basis: str
    unavailable_reason: str
    paper: LiteraturePaperRow | None
    review_warnings: list[str]


def append_unique(items: list[str], value: str) -> list[str]:
    if value and value not in items:
        return [*items, value]
    return items


def review_warnings_for(paper: LiteraturePaperRow) -> list[str]:
    warnings: list[str] = []
    for limitation in paper.limitations:
        warnings = append_unique(warnings, limitation)
    warnings = append_unique(warnings, VERIFY_METADATA_WARNING)
    return append_unique(warnings, OPENALEX_METADATA_WARNING)


def empty_detail_response(
    stage: StageCard,
    requested_paper_ref: str,
    unavailable_reason: str,
) -> LiteraturePaperDetailResponse:
    return LiteraturePaperDetailResponse(
        paper=None,
        paper_ref=requested_paper_ref,
        review_warnings=[],
        score_basis="",
        search_query="",
        source="",
        stage_id=stage.id,
        unavailable_reason=unavailable_reason,
    )


def complete_detail_response(
    stage: StageCard,
    requested_paper_ref: str,
    paper: LiteraturePaperRow,
) -> LiteraturePaperDetailResponse:
    return LiteraturePaperDetailResponse(
        paper=paper,
        paper_ref=requested_paper_ref,
        review_warnings=review_warnings_for(paper),
        score_basis=read_text(stage.output_payload, "score_basis"),
        search_query=read_text(stage.output_payload, "search_query"),
        source=read_text(stage.output_payload, "source"),
        stage_id=stage.id,
        unavailable_reason="",
    )


def find_paper(stage: StageCard, requested_paper_ref: str) -> LiteraturePaperRow:
    for paper_payload in read_paper_payloads(stage.output_payload):
        if paper_ref(paper_payload) == requested_paper_ref:
            return paper_row(paper_payload)
    raise LiteraturePaperNotFoundError(stage_id=stage.id, paper_ref=requested_paper_ref)


def build_literature_paper_detail(
    stage: StageCard,
    requested_paper_ref: str,
) -> LiteraturePaperDetailResponse:
    if stage.agent_id != LITERATURE_SCOUT_AGENT_ID:
        return empty_detail_response(stage, requested_paper_ref, WRONG_STAGE_DETAIL_REASON)
    match stage.status:
        case StageStatus.COMPLETE:
            paper = find_paper(stage, requested_paper_ref)
            return complete_detail_response(stage, requested_paper_ref, paper)
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            return empty_detail_response(stage, requested_paper_ref, INCOMPLETE_DETAIL_REASON)
        case unreachable:
            assert_never(unreachable)
