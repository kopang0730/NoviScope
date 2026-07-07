import json
from typing import Annotated, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import JsonValue
from sqlmodel import Session

from noviscope.api.artifacts import MARKDOWN_ARTIFACT_KEYS, artifact_filename
from noviscope.api.dependencies import get_session
from noviscope.api.quest_exports import (
    QuestExportStage,
    build_trust_summary,
    quest_export_stage,
)
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import PAPER_MEETING_WRITER_AGENT_ID
from noviscope.models.quest import Quest, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

MARKDOWN_MEDIA_TYPE: Final = "text/markdown; charset=utf-8"
REVIEW_PACKET_NOTE: Final = (
    "Review-only export. This packet serializes saved NoviScope workflow state "
    "and does not claim unfinished experiments are complete."
)


def label_from_value(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def slugify(value: str) -> str:
    slug_chars: list[str] = []
    separator_active = False
    for char in value.lower():
        if char.isalnum():
            slug_chars.append(char)
            separator_active = False
        elif not separator_active:
            slug_chars.append("-")
            separator_active = True
    slug = "".join(slug_chars).strip("-")
    return slug or "noviscope-quest"


def quest_review_packet_filename(quest: Quest) -> str:
    return f"{slugify(quest.title)}-review-packet.md"


def stage_review_packet_filename(stage: QuestExportStage) -> str:
    return f"{slugify(stage.title)}-{stage.id}-review-packet.md"


def append_field(lines: list[str], label: str, value: str) -> None:
    lines.append(f"- **{label}:** {value or 'Not available'}")


def human_review_state(stage: QuestExportStage) -> str:
    match stage.human_approved:
        case True:
            return "Approved"
        case False:
            return "Rejected"
        case None:
            return "Pending review"
        case unreachable:
            assert_never(unreachable)


def json_block(payload: JsonObject) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return f"```json\n{encoded}\n```"


def json_string(payload: JsonObject, key: str) -> str:
    value: JsonValue | None = payload.get(key)
    match value:
        case str() as text:
            return text
        case None | bool() | int() | float() | list() | dict():
            return ""
        case unreachable:
            assert_never(unreachable)


def append_safety_notes(lines: list[str]) -> None:
    lines.extend(
        [
            "## Safety And Traceability Notes",
            "",
            "- Model-generated hypotheses and draft writing remain under human review.",
            "- Experiment plans are not experiment results.",
            "- Verify primary papers before formal submission.",
            "- JSON payloads below are the auditable source for summarized claims.",
            "- Secret-like fields and raw provider responses are omitted from payloads.",
            "",
        ]
    )


def append_quest_metadata(lines: list[str], quest: Quest, stages: list[QuestExportStage]) -> None:
    complete_count = sum(1 for stage in stages if stage.status == StageStatus.COMPLETE)
    blocked_count = sum(1 for stage in stages if stage.status == StageStatus.BLOCKED)
    lines.extend(["## Quest Metadata", ""])
    append_field(lines, "Quest ID", quest.id)
    append_field(lines, "Status", label_from_value(quest.status.value))
    append_field(lines, "Created", quest.created_at)
    append_field(lines, "Updated", quest.updated_at)
    append_field(
        lines,
        "Stage progress",
        f"{complete_count}/{len(stages)} complete, {blocked_count} blocked",
    )
    lines.extend(["", "## Initial Research Direction", "", quest.initial_direction, ""])


def append_trust_summary(lines: list[str], stages: list[QuestExportStage]) -> None:
    summary = build_trust_summary(stages)
    lines.extend(["## Trust Summary", ""])
    append_field(lines, "Total stages", str(summary.total_stages))
    append_field(lines, "Complete stages", str(summary.complete_stages))
    append_field(lines, "Blocked stages", str(summary.blocked_stages))
    append_field(lines, "Pending review stages", str(summary.pending_review_stages))
    append_field(lines, "Low confidence stages", str(summary.low_confidence_stages))
    append_field(lines, "Available artifacts", str(summary.artifact_available_count))
    if summary.warnings:
        lines.extend(["", "### Review Warnings", ""])
        lines.extend(f"- {warning}" for warning in summary.warnings)
    lines.append("")


def append_stage_review_details(lines: list[str], stage: QuestExportStage) -> None:
    append_field(lines, "Stage ID", stage.id)
    append_field(lines, "Agent ID", stage.agent_id)
    append_field(lines, "Status", label_from_value(stage.status.value))
    append_field(lines, "Confidence", label_from_value(stage.confidence))
    append_field(lines, "Human review", human_review_state(stage))
    append_field(lines, "Updated", stage.updated_at)
    append_field(lines, "Summary", stage.summary)
    append_field(lines, "Review notes", stage.review_notes)
    if stage.hidden_payload_fields:
        append_field(lines, "Hidden payload fields", ", ".join(stage.hidden_payload_fields))
    lines.extend(["", "#### Input Payload", "", json_block(stage.input_payload)])
    lines.extend(["", "#### Output Payload", "", json_block(stage.output_payload)])
    lines.extend(["", "#### Evidence Payload", "", json_block(stage.evidence_payload)])


def append_stage_trace(lines: list[str], stages: list[QuestExportStage]) -> None:
    lines.append("## Workflow Trace")
    for index, stage in enumerate(stages, start=1):
        lines.extend(["", f"### {index}. {stage.title}", ""])
        append_stage_review_details(lines, stage)


def append_paper_artifacts(lines: list[str], stages: list[QuestExportStage]) -> None:
    paper_stage = next(
        (stage for stage in stages if stage.agent_id == PAPER_MEETING_WRITER_AGENT_ID),
        None,
    )
    lines.extend(["", "## Paper And Meeting Draft Artifacts", ""])
    if paper_stage is None or paper_stage.status != StageStatus.COMPLETE:
        lines.append("_No paper or meeting draft artifacts have been generated yet._")
        return
    for key in MARKDOWN_ARTIFACT_KEYS:
        content = json_string(paper_stage.output_payload, key.value).strip()
        lines.extend(["", f"### Artifact: {artifact_filename(key)}", ""])
        lines.append(content or "_No saved content._")


def build_quest_review_packet(quest: Quest, stages: list[QuestExportStage]) -> str:
    lines = [
        f"# NoviScope Quest Review Packet: {quest.title}",
        "",
        f"> {REVIEW_PACKET_NOTE}",
        "",
    ]
    append_safety_notes(lines)
    append_quest_metadata(lines, quest, stages)
    append_trust_summary(lines, stages)
    append_stage_trace(lines, stages)
    append_paper_artifacts(lines, stages)
    lines.extend(["", "---", "", "Generated by NoviScope from saved workflow state."])
    return "\n".join(lines) + "\n"


def build_stage_review_packet(stage: QuestExportStage) -> str:
    lines = [
        f"# NoviScope Stage Review Packet: {stage.title}",
        "",
        f"> {REVIEW_PACKET_NOTE}",
        "",
    ]
    append_safety_notes(lines)
    lines.extend(["## Stage Metadata", ""])
    append_stage_review_details(lines, stage)
    lines.extend(["", "---", "", "Generated by NoviScope from saved workflow state."])
    return "\n".join(lines) + "\n"


@router.get("/quests/{quest_id}/review-packet/download")
def download_quest_review_packet(
    quest_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    service = QuestService(session)
    try:
        quest = service.get_quest_for_user(quest_id, current_user)
        stages = [quest_export_stage(stage) for stage in service.list_stage_cards(quest.id)]
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return Response(
        content=build_quest_review_packet(quest, stages),
        headers={
            "Content-Disposition": (f'attachment; filename="{quest_review_packet_filename(quest)}"')
        },
        media_type=MARKDOWN_MEDIA_TYPE,
    )


@router.get("/stages/{stage_id}/review-packet/download")
def download_stage_review_packet(
    stage_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    service = QuestService(session)
    try:
        stage = quest_export_stage(service.get_stage_card_for_user(stage_id, current_user))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return Response(
        content=build_stage_review_packet(stage),
        headers={
            "Content-Disposition": (f'attachment; filename="{stage_review_packet_filename(stage)}"')
        },
        media_type=MARKDOWN_MEDIA_TYPE,
    )
