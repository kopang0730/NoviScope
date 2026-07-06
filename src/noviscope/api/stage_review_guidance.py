from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    StageConfidence,
    normalize_stage_output_payload,
    stage_confidence,
)
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

PENDING_REVIEW_REASON: Final = "Stage must complete before human review approval."
PENDING_REVIEW_CHECKLIST_ITEM: Final = "Run or complete this stage before human review."
FALLBACK_REVIEW_CHECKLIST_ITEM: Final = "Review the structured stage output before approving it."
CHECKLIST_SOURCE_KEYS: Final[tuple[str, ...]] = (
    "suggested_human_checklist",
    "human_review_required",
    "missing_evidence",
    "risks",
)
EVIDENCE_SOURCE_KEYS: Final[tuple[str, ...]] = (
    "evidence_for_demand",
    "evidence",
    "verified_facts",
)


class ReviewApprovalState(StrEnum):
    PENDING_STAGE_COMPLETION = "pending_stage_completion"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class StageReviewGuidanceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_id: str
    agent_id: str
    status: StageStatus
    approval_state: ReviewApprovalState
    review_required: bool
    can_approve: bool
    blocking_reason: str
    confidence: StageConfidence
    checklist: list[str]
    evidence_summary: list[str]
    warnings: list[str]
    review_notes: str


@dataclass(frozen=True, slots=True)
class StageReviewGuidanceContext:
    session: Session
    current_user: User


def get_stage_review_guidance_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StageReviewGuidanceContext:
    return StageReviewGuidanceContext(current_user=current_user, session=session)


def read_string_items(values: list[JsonValue]) -> list[str]:
    strings: list[str] = []
    for value in values:
        match value:
            case str() as text:
                if text.strip():
                    strings.append(text.strip())
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


def read_keyed_lists(payload: JsonObject, keys: tuple[str, ...]) -> list[str]:
    items: list[str] = []
    for key in keys:
        items.extend(read_string_list(payload, key))
    return items


def review_approval_state(stage: StageCard) -> ReviewApprovalState:
    match stage.status:
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            return ReviewApprovalState.PENDING_STAGE_COMPLETION
        case StageStatus.COMPLETE:
            if stage.human_approved is True:
                return ReviewApprovalState.APPROVED
            if stage.human_approved is False:
                return ReviewApprovalState.REJECTED
            return ReviewApprovalState.READY_FOR_REVIEW
        case unreachable:
            assert_never(unreachable)


def can_approve_for_state(state: ReviewApprovalState) -> bool:
    match state:
        case ReviewApprovalState.READY_FOR_REVIEW:
            return True
        case (
            ReviewApprovalState.PENDING_STAGE_COMPLETION
            | ReviewApprovalState.APPROVED
            | ReviewApprovalState.REJECTED
        ):
            return False
        case unreachable:
            assert_never(unreachable)


def review_required_for_state(state: ReviewApprovalState) -> bool:
    match state:
        case ReviewApprovalState.READY_FOR_REVIEW:
            return True
        case (
            ReviewApprovalState.PENDING_STAGE_COMPLETION
            | ReviewApprovalState.APPROVED
            | ReviewApprovalState.REJECTED
        ):
            return False
        case unreachable:
            assert_never(unreachable)


def blocking_reason_for_state(state: ReviewApprovalState) -> str:
    match state:
        case ReviewApprovalState.PENDING_STAGE_COMPLETION:
            return PENDING_REVIEW_REASON
        case (
            ReviewApprovalState.READY_FOR_REVIEW
            | ReviewApprovalState.APPROVED
            | ReviewApprovalState.REJECTED
        ):
            return ""
        case unreachable:
            assert_never(unreachable)


def checklist_for_state(state: ReviewApprovalState, output_payload: JsonObject) -> list[str]:
    match state:
        case ReviewApprovalState.PENDING_STAGE_COMPLETION:
            return [PENDING_REVIEW_CHECKLIST_ITEM]
        case (
            ReviewApprovalState.READY_FOR_REVIEW
            | ReviewApprovalState.APPROVED
            | ReviewApprovalState.REJECTED
        ):
            checklist = read_keyed_lists(output_payload, CHECKLIST_SOURCE_KEYS)
            if checklist:
                return checklist
            return [FALLBACK_REVIEW_CHECKLIST_ITEM]
        case unreachable:
            assert_never(unreachable)


def build_stage_review_guidance(stage: StageCard) -> StageReviewGuidanceResponse:
    output_payload = normalize_stage_output_payload(stage.agent_id, stage.output_payload)
    approval_state = review_approval_state(stage)
    return StageReviewGuidanceResponse(
        agent_id=stage.agent_id,
        approval_state=approval_state,
        blocking_reason=blocking_reason_for_state(approval_state),
        can_approve=can_approve_for_state(approval_state),
        checklist=checklist_for_state(approval_state, output_payload),
        confidence=stage_confidence(stage.agent_id, output_payload),
        evidence_summary=read_keyed_lists(output_payload, EVIDENCE_SOURCE_KEYS),
        review_notes=stage.review_notes,
        review_required=review_required_for_state(approval_state),
        stage_id=stage.id,
        status=stage.status,
        warnings=read_string_list(output_payload, "warnings"),
    )


@router.get("/stages/{stage_id}/review-guidance", response_model=StageReviewGuidanceResponse)
def get_stage_review_guidance(
    stage_id: str,
    context: Annotated[
        StageReviewGuidanceContext,
        Depends(get_stage_review_guidance_context),
    ],
) -> StageReviewGuidanceResponse:
    service = QuestService(context.session)
    try:
        stage = service.get_stage_card_for_user(stage_id, context.current_user)
        return build_stage_review_guidance(stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
