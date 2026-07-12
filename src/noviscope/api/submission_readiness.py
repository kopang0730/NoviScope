from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, ClassVar, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from noviscope.agents.registry import AGENT_REGISTRY
from noviscope.api.artifacts import build_artifact_manifest
from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    PAPER_MEETING_WRITER_AGENT_ID,
    StageConfidence,
    stage_confidence,
)
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

HUMAN_REVIEW_REQUIRED_KEY: Final = "human_review_required"
EXPERIMENT_RESULTS_MISSING_KEY: Final = "experiment_results_not_available"


class SubmissionReadinessStatus(StrEnum):
    BLOCKED = "blocked"
    REVIEW_READY = "review_ready"
    SUBMISSION_READY = "submission_ready"


class StageSubmissionCheckResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agent_id: str
    blocking_reasons: tuple[str, ...]
    confidence: StageConfidence
    human_approved: bool | None
    ready_for_submission: bool
    stage_id: str
    status: StageStatus
    title: str


class SubmissionReadinessResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    available_artifact_count: int
    can_use_for_formal_submission: bool
    can_use_for_meeting: bool
    complete_stage_count: int
    formal_submission_blockers: tuple[str, ...]
    overall_status: SubmissionReadinessStatus
    quest_id: str
    review_warnings: tuple[str, ...]
    stage_checks: tuple[StageSubmissionCheckResponse, ...]
    total_stage_count: int


@dataclass(frozen=True, slots=True)
class SubmissionReadinessInputs:
    available_artifact_count: int
    formal_submission_blockers: tuple[str, ...]
    review_warnings: tuple[str, ...]
    stage_checks: tuple[StageSubmissionCheckResponse, ...]


def read_string_list(payload: JsonObject, key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def paper_artifact_count(stage: StageCard) -> int:
    if stage.agent_id != PAPER_MEETING_WRITER_AGENT_ID:
        return 0
    manifest = build_artifact_manifest(stage)
    return sum(artifact.available for artifact in manifest.artifacts)


def stage_completed(stage: StageCard) -> bool:
    match stage.status:
        case StageStatus.COMPLETE:
            return True
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            return False
        case unreachable:
            assert_never(unreachable)


def base_stage_blocking_reasons(stage: StageCard) -> list[str]:
    reasons: list[str] = []
    if not stage_completed(stage):
        reasons.append("stage_not_complete")
        return reasons
    if stage.human_approved is not True:
        reasons.append("human_review_pending")
    if stage_confidence(stage.agent_id, stage.output_payload) == "low":
        reasons.append("low_confidence")
    return reasons


def paper_stage_blocking_reasons(stage: StageCard, current_reasons: list[str]) -> list[str]:
    if stage.agent_id != PAPER_MEETING_WRITER_AGENT_ID or not stage_completed(stage):
        return current_reasons
    reasons = [*current_reasons]
    if paper_artifact_count(stage) == 0:
        reasons.append("paper_artifacts_missing")
    if read_string_list(stage.output_payload, EXPERIMENT_RESULTS_MISSING_KEY):
        reasons.append("experiment_results_not_available")
    if read_string_list(stage.output_payload, HUMAN_REVIEW_REQUIRED_KEY):
        reasons.append("paper_human_review_required")
    return reasons


def build_stage_check(stage: StageCard) -> StageSubmissionCheckResponse:
    base_reasons = base_stage_blocking_reasons(stage)
    blocking_reasons = tuple(paper_stage_blocking_reasons(stage, base_reasons))
    return StageSubmissionCheckResponse(
        agent_id=stage.agent_id,
        blocking_reasons=blocking_reasons,
        confidence=stage_confidence(stage.agent_id, stage.output_payload),
        human_approved=stage.human_approved,
        ready_for_submission=not blocking_reasons,
        stage_id=stage.id,
        status=stage.status,
        title=stage.title,
    )


def stage_blocker_message(stage_check: StageSubmissionCheckResponse) -> str | None:
    display_name = AGENT_REGISTRY[stage_check.agent_id].display_name
    if "stage_not_complete" in stage_check.blocking_reasons:
        return f"{display_name} is not complete."
    if "human_review_pending" in stage_check.blocking_reasons:
        return f"{display_name} is complete but not human-approved."
    if "low_confidence" in stage_check.blocking_reasons:
        return f"{display_name} has low confidence."
    return None


def paper_blocker_messages(stage: StageCard) -> tuple[str, ...]:
    if stage.agent_id != PAPER_MEETING_WRITER_AGENT_ID or not stage_completed(stage):
        return ()
    messages: list[str] = []
    if paper_artifact_count(stage) == 0:
        messages.append("Paper artifacts are not available.")
    if read_string_list(stage.output_payload, EXPERIMENT_RESULTS_MISSING_KEY):
        messages.append("Experiment results are not available.")
    if read_string_list(stage.output_payload, HUMAN_REVIEW_REQUIRED_KEY):
        messages.append("Paper draft still has human-review items.")
    return tuple(messages)


def paper_review_warnings(stage: StageCard) -> tuple[str, ...]:
    if stage.agent_id != PAPER_MEETING_WRITER_AGENT_ID or not stage_completed(stage):
        return ()
    warnings: list[str] = []
    if read_string_list(stage.output_payload, EXPERIMENT_RESULTS_MISSING_KEY):
        warnings.append(
            "Experiment results are not available; do not present draft as validated results."
        )
    if read_string_list(stage.output_payload, HUMAN_REVIEW_REQUIRED_KEY):
        warnings.append("Paper draft still has human-review items.")
    return tuple(warnings)


def collect_readiness_inputs(stages: list[StageCard]) -> SubmissionReadinessInputs:
    stage_checks = tuple(build_stage_check(stage) for stage in stages)
    stage_blockers = tuple(
        message
        for stage_check in stage_checks
        if (message := stage_blocker_message(stage_check)) is not None
    )
    paper_blockers = tuple(message for stage in stages for message in paper_blocker_messages(stage))
    review_warnings = tuple(warning for stage in stages for warning in paper_review_warnings(stage))
    return SubmissionReadinessInputs(
        available_artifact_count=sum(paper_artifact_count(stage) for stage in stages),
        formal_submission_blockers=(*stage_blockers, *paper_blockers),
        review_warnings=review_warnings,
        stage_checks=stage_checks,
    )


def readiness_status(inputs: SubmissionReadinessInputs) -> SubmissionReadinessStatus:
    if inputs.available_artifact_count == 0:
        return SubmissionReadinessStatus.BLOCKED
    if inputs.formal_submission_blockers:
        return SubmissionReadinessStatus.REVIEW_READY
    return SubmissionReadinessStatus.SUBMISSION_READY


def build_submission_readiness(
    quest_id: str,
    stages: list[StageCard],
) -> SubmissionReadinessResponse:
    inputs = collect_readiness_inputs(stages)
    overall_status = readiness_status(inputs)
    return SubmissionReadinessResponse(
        available_artifact_count=inputs.available_artifact_count,
        can_use_for_formal_submission=overall_status == SubmissionReadinessStatus.SUBMISSION_READY,
        can_use_for_meeting=inputs.available_artifact_count > 0,
        complete_stage_count=sum(stage_completed(stage) for stage in stages),
        formal_submission_blockers=inputs.formal_submission_blockers,
        overall_status=overall_status,
        quest_id=quest_id,
        review_warnings=inputs.review_warnings,
        stage_checks=inputs.stage_checks,
        total_stage_count=len(stages),
    )


@router.get("/quests/{quest_id}/submission-readiness", response_model=SubmissionReadinessResponse)
def get_quest_submission_readiness(
    quest_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SubmissionReadinessResponse:
    service = QuestService(session)
    try:
        quest = service.get_quest_for_user(quest_id, current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return build_submission_readiness(quest.id, service.list_stage_cards(quest.id))
