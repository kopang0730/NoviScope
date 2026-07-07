from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.api.evidence_audit_contract import QuestEvidenceAuditResponse
from noviscope.api.evidence_audit_rules import build_quest_evidence_audit
from noviscope.auth.dependencies import get_current_user
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()


@dataclass(frozen=True, slots=True)
class EvidenceAuditContext:
    session: Session
    current_user: User


def get_evidence_audit_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvidenceAuditContext:
    return EvidenceAuditContext(current_user=current_user, session=session)


@router.get("/quests/{quest_id}/evidence-audit", response_model=QuestEvidenceAuditResponse)
def get_quest_evidence_audit(
    quest_id: str,
    context: Annotated[EvidenceAuditContext, Depends(get_evidence_audit_context)],
) -> QuestEvidenceAuditResponse:
    service = QuestService(context.session)
    try:
        _ = service.get_quest_for_user(quest_id, context.current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return build_quest_evidence_audit(quest_id, service.list_stage_cards(quest_id))
