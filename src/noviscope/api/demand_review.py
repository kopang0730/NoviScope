from enum import StrEnum
from typing import Annotated, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.api.routes import StageCardResponse, stage_response
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import DEMAND_VALIDATOR_AGENT_ID
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
APPROVING_VERDICTS: Final = frozenset({"plausible", "verified"})


class DemandReviewVerdict(StrEnum):
    VERIFIED = "verified"
    PLAUSIBLE = "plausible"
    UNCLEAR = "unclear"
    REJECTED = "rejected"


class DemandReviewError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class DemandReviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    verdict: DemandReviewVerdict
    sources: list[NonEmptyStr] = []
    review_notes: str = ""


@router.post("/stages/{stage_id}/demand-review", response_model=StageCardResponse)
def review_demand(
    stage_id: str,
    request: DemandReviewRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StageCardResponse:
    service = QuestService(session)
    try:
        stage = service.get_stage_card_for_user(stage_id, current_user)
        ensure_reviewable_demand_stage(stage)
        validate_sources(request)
        updated_stage = service.update_stage_card(
            stage_id,
            evidence_payload=demand_review_evidence(stage.evidence_payload, request),
            human_approved=demand_approved(request.verdict),
            human_approved_set=True,
            review_notes=request.review_notes,
            summary=demand_review_summary(request.verdict),
        )
        return stage_response(updated_stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DemandReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc


def ensure_reviewable_demand_stage(stage: StageCard) -> None:
    if stage.agent_id != DEMAND_VALIDATOR_AGENT_ID:
        raise DemandReviewError("Demand review is only available for Demand validation.")
    if stage.status != StageStatus.COMPLETE:
        raise DemandReviewError("Demand validation must complete before human review.")


def validate_sources(request: DemandReviewRequest) -> None:
    if demand_approved(request.verdict) and not request.sources:
        raise DemandReviewError(
            "At least one demand evidence source is required to approve demand."
        )


def demand_review_evidence(
    existing_evidence: JsonObject,
    request: DemandReviewRequest,
) -> JsonObject:
    return {
        **existing_evidence,
        "human_demand_reviewed": True,
        "human_demand_sources": request.sources,
        "human_demand_verdict": request.verdict.value,
        "human_go_or_no_go": demand_go_or_no_go(request.verdict),
    }


def demand_approved(verdict: DemandReviewVerdict) -> bool:
    return verdict.value in APPROVING_VERDICTS


def demand_go_or_no_go(verdict: DemandReviewVerdict) -> str:
    match verdict:
        case DemandReviewVerdict.VERIFIED:
            return "go"
        case DemandReviewVerdict.PLAUSIBLE:
            return "go_with_human_review"
        case DemandReviewVerdict.UNCLEAR:
            return "needs_more_evidence"
        case DemandReviewVerdict.REJECTED:
            return "no_go"
        case unreachable:
            assert_never(unreachable)


def demand_review_summary(verdict: DemandReviewVerdict) -> str:
    match verdict:
        case DemandReviewVerdict.VERIFIED:
            return "Human review approved demand validation as verified."
        case DemandReviewVerdict.PLAUSIBLE:
            return "Human review approved demand validation as plausible."
        case DemandReviewVerdict.UNCLEAR:
            return "Human review marked demand validation as needing more evidence."
        case DemandReviewVerdict.REJECTED:
            return "Human review rejected demand validation."
        case unreachable:
            assert_never(unreachable)
