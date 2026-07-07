from dataclasses import dataclass
from typing import Annotated, ClassVar, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlmodel import Session

from noviscope.api.artifacts import (
    MarkdownArtifactManifestItem,
    build_artifact_manifest,
)
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

INCOMPLETE_STAGE_REASON: Final = (
    "Paper & Meeting Writer must complete before writing claim matrix rows are available."
)
WRONG_STAGE_REASON: Final = "This stage does not expose Paper & Meeting Writer claims."


@dataclass(frozen=True, slots=True)
class ClaimGroupSpec:
    group_id: str
    title: str
    payload_key: str
    requires_human_review: bool


CLAIM_GROUP_SPECS: Final[tuple[ClaimGroupSpec, ...]] = (
    ClaimGroupSpec("verified_facts", "Verified facts", "verified_facts", False),
    ClaimGroupSpec(
        "model_generated_hypotheses",
        "Model-generated hypotheses",
        "model_generated_hypotheses",
        True,
    ),
    ClaimGroupSpec(
        "experiment_results_not_available",
        "Experiment results not available",
        "experiment_results_not_available",
        True,
    ),
    ClaimGroupSpec("human_review_required", "Human review required", "human_review_required", True),
)


class WritingClaimGroupResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    group_id: str
    items: list[str]
    requires_human_review: bool
    title: str


class WritingClaimMatrixResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    artifacts: list[MarkdownArtifactManifestItem]
    claim_groups: list[WritingClaimGroupResponse]
    confidence: StageConfidence
    no_experiment_results: bool
    requires_human_review: bool
    source_stage_ids: dict[str, str]
    stage_id: str
    status: StageStatus
    summary: str
    unavailable_reason: str
    warnings: list[str]


def string_items(items: list[JsonValue]) -> list[str]:
    values: list[str] = []
    for item in items:
        match item:
            case str() as value:
                if value:
                    values.append(value)
            case None | bool() | int() | float() | list() | dict():
                continue
            case unreachable:
                assert_never(unreachable)
    return values


def read_text(payload: JsonObject, key: str) -> str:
    value = payload.get(key)
    match value:
        case str() as text:
            return text
        case None | bool() | int() | float() | list() | dict():
            return ""
        case unreachable:
            assert_never(unreachable)


def read_string_list(payload: JsonObject, key: str) -> list[str]:
    value = payload.get(key)
    match value:
        case list() as items:
            return string_items(items)
        case None | str() | bool() | int() | float() | dict():
            return []
        case unreachable:
            assert_never(unreachable)


def read_source_stage_ids(payload: JsonObject) -> dict[str, str]:
    value = payload.get("source_stage_ids")
    match value:
        case dict() as mapping:
            return {
                key: item
                for key, item in mapping.items()
                if isinstance(key, str) and isinstance(item, str)
            }
        case None | str() | bool() | int() | float() | list():
            return {}
        case unreachable:
            assert_never(unreachable)


def claim_group(stage: StageCard, spec: ClaimGroupSpec) -> WritingClaimGroupResponse:
    return WritingClaimGroupResponse(
        group_id=spec.group_id,
        items=read_string_list(stage.output_payload, spec.payload_key),
        requires_human_review=spec.requires_human_review,
        title=spec.title,
    )


def empty_response(stage: StageCard, reason: str) -> WritingClaimMatrixResponse:
    return WritingClaimMatrixResponse(
        artifacts=[],
        claim_groups=[],
        confidence=stage_confidence(stage.agent_id, stage.output_payload),
        no_experiment_results=True,
        requires_human_review=True,
        source_stage_ids=read_source_stage_ids(stage.output_payload),
        stage_id=stage.id,
        status=stage.status,
        summary=stage.summary,
        unavailable_reason=reason,
        warnings=[],
    )


def build_writing_claim_matrix(stage: StageCard) -> WritingClaimMatrixResponse:
    if stage.agent_id != PAPER_MEETING_WRITER_AGENT_ID:
        return empty_response(stage, WRONG_STAGE_REASON)
    if stage.status != StageStatus.COMPLETE:
        return empty_response(stage, INCOMPLETE_STAGE_REASON)

    return WritingClaimMatrixResponse(
        artifacts=build_artifact_manifest(stage).artifacts,
        claim_groups=[claim_group(stage, spec) for spec in CLAIM_GROUP_SPECS],
        confidence=stage_confidence(stage.agent_id, stage.output_payload),
        no_experiment_results=True,
        requires_human_review=True,
        source_stage_ids=read_source_stage_ids(stage.output_payload),
        stage_id=stage.id,
        status=stage.status,
        summary=read_text(stage.output_payload, "summary") or stage.summary,
        unavailable_reason="",
        warnings=read_string_list(stage.output_payload, "warnings"),
    )


@router.get(
    "/stages/{stage_id}/writing-claim-matrix",
    response_model=WritingClaimMatrixResponse,
)
def get_writing_claim_matrix(
    stage_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WritingClaimMatrixResponse:
    service = QuestService(session)
    try:
        stage = service.get_stage_card_for_user(stage_id, current_user)
        return build_writing_claim_matrix(stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
