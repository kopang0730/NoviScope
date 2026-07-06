from dataclasses import dataclass
from typing import Annotated, ClassVar, Final

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import StageConfidence, stage_confidence
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

SOURCE_REF_KEYS: Final[tuple[str, ...]] = (
    "evidence",
    "evidence_for_demand",
    "missing_evidence",
    "sources",
)
PAPER_COLLECTION_KEYS: Final[tuple[str, ...]] = ("papers", "top_papers")
PAPER_REF_KEYS: Final[tuple[str, ...]] = ("arxiv_id", "doi", "paper_ref", "title", "url")


@dataclass(frozen=True, slots=True)
class EvidenceLedgerContext:
    session: Session
    current_user: User


class EvidenceLedgerEntryResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agent_id: str
    confidence: StageConfidence
    evidence_keys: tuple[str, ...]
    human_approved: bool | None
    output_keys: tuple[str, ...]
    provider_id: str
    provider_model: str
    requires_human_review: bool
    review_notes: str
    source_count: int
    source_policy: str
    source_refs: tuple[str, ...]
    stage_id: str
    stage_status: StageStatus
    stage_title: str
    summary: str


class QuestEvidenceLedgerResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    entries: tuple[EvidenceLedgerEntryResponse, ...]
    evidence_entry_count: int
    missing_evidence_count: int
    quest_id: str
    requires_human_review_count: int
    total_stage_count: int


def get_evidence_ledger_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvidenceLedgerContext:
    return EvidenceLedgerContext(current_user=current_user, session=session)


def read_string(payload: JsonObject, key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str):
        return value.strip()
    return ""


def read_bool(payload: JsonObject, key: str) -> bool:
    value = payload.get(key)
    if isinstance(value, bool):
        return value
    return False


def read_source_refs(value: JsonValue | None) -> tuple[str, ...]:
    if isinstance(value, str):
        stripped_value = value.strip()
        return (stripped_value,) if stripped_value else ()
    if isinstance(value, list):
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    return ()


def read_paper_refs(value: JsonValue | None) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    refs: list[str] = []
    for item in value:
        if isinstance(item, dict):
            refs.extend(read_string(item, key) for key in PAPER_REF_KEYS)
    return tuple(ref for ref in refs if ref)


def collect_source_refs(stage: StageCard) -> tuple[str, ...]:
    refs: list[str] = []
    for key in SOURCE_REF_KEYS:
        refs.extend(read_source_refs(stage.evidence_payload.get(key)))
        refs.extend(read_source_refs(stage.output_payload.get(key)))
    for key in PAPER_COLLECTION_KEYS:
        refs.extend(read_paper_refs(stage.output_payload.get(key)))
    return tuple(dict.fromkeys(refs))


def build_evidence_ledger_entry(stage: StageCard) -> EvidenceLedgerEntryResponse:
    source_refs = collect_source_refs(stage)
    return EvidenceLedgerEntryResponse(
        agent_id=stage.agent_id,
        confidence=stage_confidence(stage.agent_id, stage.output_payload),
        evidence_keys=tuple(sorted(stage.evidence_payload)),
        human_approved=stage.human_approved,
        output_keys=tuple(sorted(stage.output_payload)),
        provider_id=read_string(stage.evidence_payload, "provider_id"),
        provider_model=read_string(stage.evidence_payload, "provider_model"),
        requires_human_review=(
            read_bool(stage.evidence_payload, "requires_human_review")
            or stage.human_approved is False
        ),
        review_notes=stage.review_notes,
        source_count=len(source_refs),
        source_policy=(
            read_string(stage.evidence_payload, "source_policy") or "no_evidence_recorded"
        ),
        source_refs=source_refs,
        stage_id=stage.id,
        stage_status=stage.status,
        stage_title=stage.title,
        summary=stage.summary,
    )


def build_quest_evidence_ledger(
    quest_id: str,
    stages: list[StageCard],
) -> QuestEvidenceLedgerResponse:
    entries = tuple(build_evidence_ledger_entry(stage) for stage in stages)
    return QuestEvidenceLedgerResponse(
        entries=entries,
        evidence_entry_count=sum(entry.source_count > 0 for entry in entries),
        missing_evidence_count=sum(entry.source_count == 0 for entry in entries),
        quest_id=quest_id,
        requires_human_review_count=sum(entry.requires_human_review for entry in entries),
        total_stage_count=len(entries),
    )


@router.get("/quests/{quest_id}/evidence-ledger", response_model=QuestEvidenceLedgerResponse)
def get_quest_evidence_ledger(
    quest_id: str,
    context: Annotated[EvidenceLedgerContext, Depends(get_evidence_ledger_context)],
) -> QuestEvidenceLedgerResponse:
    service = QuestService(context.session)
    try:
        _ = service.get_quest_for_user(quest_id, context.current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return build_quest_evidence_ledger(quest_id, service.list_stage_cards(quest_id))
