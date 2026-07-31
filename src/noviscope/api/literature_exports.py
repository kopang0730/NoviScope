from typing import Annotated, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import JsonValue
from sqlmodel import Session

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.api.dependencies import get_session
from noviscope.api.stage_display_output import OUTPUT_PAYLOAD_ROOT, sanitize_json_value
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

CITATION_DOWNLOAD_MEDIA_TYPE: Final = "text/markdown; charset=utf-8"
CITATION_FILENAME: Final = "literature-scout-citations.md"
HUMAN_REVIEW_NOTE: Final = "Review OpenAlex metadata against the primary paper before citing."


def read_string(payload: JsonObject, key: str) -> str:
    value: JsonValue | None = payload.get(key)
    match value:
        case str() as text:
            return text
        case None | bool() | int() | float() | list() | dict():
            return ""
        case unreachable:
            assert_never(unreachable)


def read_number_text(payload: JsonObject, key: str) -> str:
    value: JsonValue | None = payload.get(key)
    match value:
        case bool() | None | str() | list() | dict():
            return ""
        case int() | float() as number:
            return str(number)
        case unreachable:
            assert_never(unreachable)


def read_string_array(payload: JsonObject, key: str) -> list[str]:
    value: JsonValue | None = payload.get(key)
    match value:
        case list() as values:
            strings: list[str] = []
            for item in values:
                match item:
                    case str() as text:
                        strings.append(text)
                    case None | bool() | int() | float() | list() | dict():
                        pass
                    case unreachable:
                        assert_never(unreachable)
            return strings
        case None | bool() | int() | float() | str() | dict():
            return []
        case unreachable:
            assert_never(unreachable)


def sanitized_literature_payload(stage: StageCard) -> tuple[JsonObject, list[str]]:
    sanitized = sanitize_json_value(stage.output_payload, OUTPUT_PAYLOAD_ROOT)
    match sanitized.value:
        case dict() as payload:
            return payload, sanitized.hidden_fields
        case None | bool() | int() | float() | str() | list():
            return {}, sanitized.hidden_fields
        case unreachable:
            assert_never(unreachable)


def read_literature_papers(output_payload: JsonObject) -> list[JsonObject]:
    value: JsonValue | None = output_payload.get("papers")
    match value:
        case list() as values:
            papers: list[JsonObject] = []
            for item in values:
                match item:
                    case dict() as paper:
                        papers.append(paper)
                    case None | bool() | int() | float() | str() | list():
                        pass
                    case unreachable:
                        assert_never(unreachable)
            return papers
        case None | bool() | int() | float() | str() | dict():
            return []
        case unreachable:
            assert_never(unreachable)


def append_field(lines: list[str], label: str, value: str) -> None:
    lines.append(f"- **{label}:** {value or 'Not available'}")


def best_identifier(paper: JsonObject) -> str:
    for key in ("doi", "openalex_id", "url"):
        value = read_string(paper, key)
        if value:
            return value
    return ""


def append_paper(lines: list[str], paper: JsonObject, index: int) -> None:
    authors = ", ".join(read_string_array(paper, "authors"))
    limitations = "; ".join(read_string_array(paper, "limitations"))
    quality_signals = "; ".join(read_string_array(paper, "source_quality_signals"))
    lines.extend(["", f"### {index}. {read_string(paper, 'title') or 'Untitled paper'}", ""])
    append_field(lines, "Authors", authors)
    append_field(lines, "Year", read_number_text(paper, "year"))
    append_field(lines, "Venue", read_string(paper, "venue"))
    append_field(lines, "Identifier", best_identifier(paper))
    append_field(lines, "URL", read_string(paper, "url"))
    append_field(lines, "Reliability", read_string(paper, "reliability_level"))
    append_field(lines, "Relevance score", read_number_text(paper, "relevance_score"))
    append_field(lines, "Why relevant", read_string(paper, "why_relevant"))
    append_field(lines, "Source quality signals", quality_signals)
    append_field(lines, "Limitations", limitations)


def assert_literature_stage_complete(stage: StageCard) -> None:
    if stage.agent_id != LITERATURE_SCOUT_AGENT_ID:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This stage does not expose Literature Scout citations.",
        )
    match stage.status:
        case StageStatus.COMPLETE:
            return
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Literature Scout must complete before citations can be downloaded.",
            )
        case unreachable:
            assert_never(unreachable)


def build_literature_citations_markdown(stage: StageCard) -> str:
    output_payload, hidden_fields = sanitized_literature_payload(stage)
    papers = read_literature_papers(output_payload)
    lines = [
        "# NoviScope Literature Citation List",
        "",
        f"> {HUMAN_REVIEW_NOTE}",
        "",
        "## Source",
        "",
    ]
    append_field(lines, "Stage ID", stage.id)
    append_field(lines, "Source", read_string(output_payload, "source"))
    append_field(lines, "Search query", read_string(output_payload, "search_query"))
    append_field(lines, "Score basis", read_string(output_payload, "score_basis"))
    if hidden_fields:
        append_field(lines, "Hidden payload fields", f"{len(hidden_fields)} field(s) omitted")
    lines.extend(["", "## Papers", ""])
    if not papers:
        lines.append("_No Literature Scout papers were recorded._")
    for index, paper in enumerate(papers, start=1):
        append_paper(lines, paper, index)
    lines.extend(["", "---", "", "Generated by NoviScope from saved Literature Scout metadata."])
    return "\n".join(lines) + "\n"


@router.get("/stages/{stage_id}/literature-citations/download")
def download_literature_citations(
    stage_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    service = QuestService(session)
    try:
        stage = service.get_stage_card_for_user(stage_id, current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    assert_literature_stage_complete(stage)
    return Response(
        content=build_literature_citations_markdown(stage),
        headers={"Content-Disposition": f'attachment; filename="{CITATION_FILENAME}"'},
        media_type=CITATION_DOWNLOAD_MEDIA_TYPE,
    )
