from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, ClassVar, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.stage_policy import StageConfidence, stage_confidence
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()


class StageRunProvenanceState(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class RunProvenanceContext:
    session: Session
    current_user: User


class StageRunProvenanceEntryResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agent_id: str
    blocking_detail: str
    blocking_reason: str
    can_run_recorded: bool | None
    confidence: StageConfidence
    evidence_keys: tuple[str, ...]
    has_raw_response: bool
    human_approved: bool | None
    input_keys: tuple[str, ...]
    output_keys: tuple[str, ...]
    provider_id: str
    provider_kind: str
    provider_model: str
    provider_name: str
    requires_human_review: bool
    run_state: StageRunProvenanceState
    stage_id: str
    stage_status: StageStatus
    stage_title: str
    summary: str
    updated_at: str


class QuestRunProvenanceResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    attempted_stage_count: int
    blocked_stage_count: int
    entries: tuple[StageRunProvenanceEntryResponse, ...]
    human_review_required_count: int
    missing_provider_provenance_count: int
    quest_id: str
    raw_response_count: int
    total_stage_count: int


def get_run_provenance_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RunProvenanceContext:
    return RunProvenanceContext(current_user=current_user, session=session)


def read_string_value(value: JsonValue | None) -> str:
    match value:
        case str() as text:
            return text.strip()
        case None | bool() | int() | float() | list() | dict():
            return ""
        case unreachable:
            assert_never(unreachable)


def read_bool_value(value: JsonValue | None) -> bool | None:
    match value:
        case bool() as flag:
            return flag
        case None | str() | int() | float() | list() | dict():
            return None
        case unreachable:
            assert_never(unreachable)


def stage_run_state(stage: StageCard) -> StageRunProvenanceState:
    match stage.status:
        case StageStatus.PENDING:
            return StageRunProvenanceState.NOT_STARTED
        case StageStatus.RUNNING:
            return StageRunProvenanceState.RUNNING
        case StageStatus.BLOCKED:
            return StageRunProvenanceState.BLOCKED
        case StageStatus.COMPLETE:
            return StageRunProvenanceState.COMPLETE
        case unreachable:
            assert_never(unreachable)


def provider_field(stage: StageCard, key: str) -> str:
    evidence_value = read_string_value(stage.evidence_payload.get(key))
    if evidence_value:
        return evidence_value
    return read_string_value(stage.input_payload.get(key))


def requires_human_review(stage: StageCard) -> bool:
    recorded_review = read_bool_value(stage.evidence_payload.get("requires_human_review"))
    return recorded_review is True or stage.human_approved is False


def build_run_provenance_entry(stage: StageCard) -> StageRunProvenanceEntryResponse:
    return StageRunProvenanceEntryResponse(
        agent_id=stage.agent_id,
        blocking_detail=read_string_value(stage.evidence_payload.get("blocking_detail")),
        blocking_reason=read_string_value(stage.evidence_payload.get("blocking_reason")),
        can_run_recorded=read_bool_value(stage.evidence_payload.get("can_run")),
        confidence=stage_confidence(stage.agent_id, stage.output_payload),
        evidence_keys=tuple(sorted(stage.evidence_payload)),
        has_raw_response="raw_response" in stage.output_payload,
        human_approved=stage.human_approved,
        input_keys=tuple(sorted(stage.input_payload)),
        output_keys=tuple(sorted(stage.output_payload)),
        provider_id=provider_field(stage, "provider_id"),
        provider_kind=provider_field(stage, "provider_kind"),
        provider_model=provider_field(stage, "provider_model"),
        provider_name=provider_field(stage, "provider_name"),
        requires_human_review=requires_human_review(stage),
        run_state=stage_run_state(stage),
        stage_id=stage.id,
        stage_status=stage.status,
        stage_title=stage.title,
        summary=stage.summary,
        updated_at=stage.updated_at,
    )


def build_quest_run_provenance(
    quest_id: str,
    stages: Sequence[StageCard],
) -> QuestRunProvenanceResponse:
    entries = tuple(build_run_provenance_entry(stage) for stage in stages)
    return QuestRunProvenanceResponse(
        attempted_stage_count=sum(
            entry.run_state != StageRunProvenanceState.NOT_STARTED for entry in entries
        ),
        blocked_stage_count=sum(
            entry.run_state == StageRunProvenanceState.BLOCKED for entry in entries
        ),
        entries=entries,
        human_review_required_count=sum(entry.requires_human_review for entry in entries),
        missing_provider_provenance_count=sum(
            entry.run_state == StageRunProvenanceState.COMPLETE and not entry.provider_model
            for entry in entries
        ),
        quest_id=quest_id,
        raw_response_count=sum(entry.has_raw_response for entry in entries),
        total_stage_count=len(entries),
    )


@router.get("/quests/{quest_id}/run-provenance", response_model=QuestRunProvenanceResponse)
def get_quest_run_provenance(
    quest_id: str,
    context: Annotated[RunProvenanceContext, Depends(get_run_provenance_context)],
) -> QuestRunProvenanceResponse:
    service = QuestService(context.session)
    try:
        _ = service.get_quest_for_user(quest_id, context.current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return build_quest_run_provenance(quest_id, service.list_stage_cards(quest_id))
