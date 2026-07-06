from dataclasses import dataclass
from enum import StrEnum
from typing import Final, assert_never

from pydantic import BaseModel, ConfigDict, JsonValue

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.core.json_types import JsonObject
from noviscope.models.quest import StageCard, StageStatus

INCOMPLETE_STAGE_REASON: Final = (
    "Literature Scout must complete before paper table rows are available."
)
WRONG_STAGE_REASON: Final = "This stage does not expose Literature Scout paper rows."


class LiteraturePaperSort(StrEnum):
    RELEVANCE_DESC = "relevance_desc"
    YEAR_ASC = "year_asc"
    YEAR_DESC = "year_desc"


class LiteraturePaperReliabilityLevel(StrEnum):
    ARXIV_PREPRINT = "arxiv_preprint"
    PEER_REVIEWED = "peer_reviewed"
    TOP_CONFERENCE_OR_JOURNAL = "top_conference_or_journal"
    UNKNOWN = "unknown"


class LiteraturePaperTableFilters(BaseModel):
    model_config = ConfigDict(frozen=True)

    reliability_level: LiteraturePaperReliabilityLevel | None


class LiteraturePaperRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper_ref: str
    title: str
    authors: list[str]
    year: int | None
    venue: str
    url: str
    doi: str
    abstract_summary: str
    relevance_score: float
    reliability_level: str
    why_relevant: str
    limitations: list[str]
    source_quality_signals: list[str]
    source_type: str
    publication_type: str
    recency_bucket: str


class LiteraturePaperTableResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_id: str
    source: str
    search_query: str
    score_basis: str
    total_count: int
    returned_count: int
    sort: LiteraturePaperSort
    filters: LiteraturePaperTableFilters
    unavailable_reason: str
    papers: list[LiteraturePaperRow]


@dataclass(frozen=True, slots=True)
class LiteraturePaperTableOptions:
    filters: LiteraturePaperTableFilters
    sort_mode: LiteraturePaperSort


def read_text(payload: JsonObject, key: str) -> str:
    value = payload.get(key)
    match value:
        case str() as text:
            return text
        case None | bool() | int() | float() | list() | dict():
            return ""
        case unreachable:
            assert_never(unreachable)


def read_int(payload: JsonObject, key: str) -> int | None:
    value = payload.get(key)
    match value:
        case bool():
            return None
        case int() as number:
            return number
        case None | str() | float() | list() | dict():
            return None
        case unreachable:
            assert_never(unreachable)


def read_float(payload: JsonObject, key: str) -> float:
    value = payload.get(key)
    match value:
        case bool():
            return 0.0
        case float() as number:
            return number
        case int() as number:
            return float(number)
        case None | str() | list() | dict():
            return 0.0
        case unreachable:
            assert_never(unreachable)


def read_string_items(values: list[JsonValue]) -> list[str]:
    strings: list[str] = []
    for value in values:
        match value:
            case str() as text:
                if text:
                    strings.append(text)
            case None | bool() | int() | float() | list() | dict():
                continue
            case unreachable:
                assert_never(unreachable)
    return strings


def read_string_list(payload: JsonObject, key: str) -> list[str]:
    value = payload.get(key)
    match value:
        case list() as items:
            return read_string_items(items)
        case None | str() | bool() | int() | float() | dict():
            return []
        case unreachable:
            assert_never(unreachable)


def read_paper_payloads(payload: JsonObject) -> list[JsonObject]:
    value = payload.get("papers")
    match value:
        case list() as items:
            papers: list[JsonObject] = []
            for item in items:
                match item:
                    case dict() as paper:
                        papers.append(paper)
                    case None | str() | bool() | int() | float() | list():
                        continue
                    case unreachable:
                        assert_never(unreachable)
            return papers
        case None | str() | bool() | int() | float() | dict():
            return []
        case unreachable:
            assert_never(unreachable)


def paper_ref(row: JsonObject) -> str:
    openalex_id = read_text(row, "openalex_id")
    if openalex_id:
        return openalex_id
    doi = read_text(row, "doi")
    if doi:
        return doi
    return read_text(row, "url")


def paper_row(row: JsonObject) -> LiteraturePaperRow:
    return LiteraturePaperRow(
        abstract_summary=read_text(row, "abstract_summary"),
        authors=read_string_list(row, "authors"),
        doi=read_text(row, "doi"),
        limitations=read_string_list(row, "limitations"),
        paper_ref=paper_ref(row),
        publication_type=read_text(row, "publication_type"),
        recency_bucket=read_text(row, "recency_bucket"),
        relevance_score=read_float(row, "relevance_score"),
        reliability_level=read_text(row, "reliability_level"),
        source_quality_signals=read_string_list(row, "source_quality_signals"),
        source_type=read_text(row, "source_type"),
        title=read_text(row, "title"),
        url=read_text(row, "url"),
        venue=read_text(row, "venue"),
        why_relevant=read_text(row, "why_relevant"),
        year=read_int(row, "year"),
    )


def sorted_rows(
    rows: list[LiteraturePaperRow],
    sort_mode: LiteraturePaperSort,
) -> list[LiteraturePaperRow]:
    match sort_mode:
        case LiteraturePaperSort.RELEVANCE_DESC:
            return sorted(rows, key=lambda row: row.relevance_score, reverse=True)
        case LiteraturePaperSort.YEAR_DESC:
            return sorted(rows, key=lambda row: row.year or 0, reverse=True)
        case LiteraturePaperSort.YEAR_ASC:
            return sorted(rows, key=lambda row: row.year or 9999)
        case unreachable:
            assert_never(unreachable)


def filtered_rows(
    rows: list[LiteraturePaperRow],
    reliability_level: LiteraturePaperReliabilityLevel | None,
) -> list[LiteraturePaperRow]:
    if reliability_level is None:
        return rows
    return [row for row in rows if row.reliability_level == reliability_level.value]


def empty_response(
    stage: StageCard,
    options: LiteraturePaperTableOptions,
    unavailable_reason: str,
) -> LiteraturePaperTableResponse:
    return LiteraturePaperTableResponse(
        filters=options.filters,
        papers=[],
        returned_count=0,
        score_basis="",
        search_query="",
        sort=options.sort_mode,
        source="",
        stage_id=stage.id,
        total_count=0,
        unavailable_reason=unavailable_reason,
    )


def build_literature_paper_table(
    stage: StageCard,
    options: LiteraturePaperTableOptions,
) -> LiteraturePaperTableResponse:
    if stage.agent_id != LITERATURE_SCOUT_AGENT_ID:
        return empty_response(stage, options, WRONG_STAGE_REASON)
    match stage.status:
        case StageStatus.COMPLETE:
            paper_rows = [paper_row(paper) for paper in read_paper_payloads(stage.output_payload)]
            visible_rows = sorted_rows(
                filtered_rows(paper_rows, options.filters.reliability_level),
                options.sort_mode,
            )
            return LiteraturePaperTableResponse(
                filters=options.filters,
                papers=visible_rows,
                returned_count=len(visible_rows),
                score_basis=read_text(stage.output_payload, "score_basis"),
                search_query=read_text(stage.output_payload, "search_query"),
                sort=options.sort_mode,
                source=read_text(stage.output_payload, "source"),
                stage_id=stage.id,
                total_count=len(paper_rows),
                unavailable_reason="",
            )
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            return empty_response(stage, options, INCOMPLETE_STAGE_REASON)
        case unreachable:
            assert_never(unreachable)
