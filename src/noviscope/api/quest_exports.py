from typing import Annotated, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from noviscope.api.artifacts import (
    MarkdownArtifactManifestResponse,
    build_artifact_manifest,
)
from noviscope.api.dependencies import get_session
from noviscope.api.stage_display_output import sanitize_json_value
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    PAPER_MEETING_WRITER_AGENT_ID,
    StageConfidence,
    stage_confidence,
)
from noviscope.models.common import utc_now
from noviscope.models.quest import Quest, QuestStatus, StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()


class QuestExportQuest(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    owner_user_id: str | None
    title: str
    initial_direction: str
    status: QuestStatus
    created_at: str
    updated_at: str


class QuestExportStage(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    quest_id: str
    agent_id: str
    title: str
    status: StageStatus
    confidence: StageConfidence
    summary: str
    input_payload: JsonObject
    output_payload: JsonObject
    evidence_payload: JsonObject
    hidden_payload_fields: list[str]
    human_approved: bool | None
    review_notes: str
    artifact_manifest: MarkdownArtifactManifestResponse | None
    created_at: str
    updated_at: str


class QuestExportTrustSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_stages: int
    complete_stages: int
    blocked_stages: int
    pending_review_stages: int
    low_confidence_stages: int
    artifact_available_count: int
    warnings: list[str]


class QuestExportResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: str
    quest: QuestExportQuest
    stages: list[QuestExportStage]
    trust_summary: QuestExportTrustSummary


def artifact_manifest_for_stage(stage: StageCard) -> MarkdownArtifactManifestResponse | None:
    if stage.agent_id != PAPER_MEETING_WRITER_AGENT_ID:
        return None
    return build_artifact_manifest(stage)


def quest_export_quest(quest: Quest) -> QuestExportQuest:
    return QuestExportQuest(
        created_at=quest.created_at,
        id=quest.id,
        initial_direction=quest.initial_direction,
        owner_user_id=quest.owner_user_id,
        status=quest.status,
        title=quest.title,
        updated_at=quest.updated_at,
    )


def sanitized_payload(payload: JsonObject, root_path: str) -> tuple[JsonObject, list[str]]:
    sanitized = sanitize_json_value(payload, root_path)
    match sanitized.value:
        case dict() as payload_value:
            return payload_value, sanitized.hidden_fields
        case None | str() | bool() | int() | float() | list():
            return {}, sanitized.hidden_fields
        case unreachable:
            assert_never(unreachable)


def quest_export_stage(stage: StageCard) -> QuestExportStage:
    input_payload, input_hidden_fields = sanitized_payload(stage.input_payload, "input_payload")
    output_payload, output_hidden_fields = sanitized_payload(stage.output_payload, "output_payload")
    evidence_payload, evidence_hidden_fields = sanitized_payload(
        stage.evidence_payload,
        "evidence_payload",
    )
    return QuestExportStage(
        agent_id=stage.agent_id,
        artifact_manifest=artifact_manifest_for_stage(stage),
        confidence=stage_confidence(stage.agent_id, stage.output_payload),
        created_at=stage.created_at,
        evidence_payload=evidence_payload,
        hidden_payload_fields=[
            *input_hidden_fields,
            *output_hidden_fields,
            *evidence_hidden_fields,
        ],
        human_approved=stage.human_approved,
        id=stage.id,
        input_payload=input_payload,
        output_payload=output_payload,
        quest_id=stage.quest_id,
        review_notes=stage.review_notes,
        status=stage.status,
        summary=stage.summary,
        title=stage.title,
        updated_at=stage.updated_at,
    )


def stage_export_warnings(stage: QuestExportStage) -> list[str]:
    warnings: list[str] = []
    match stage.status:
        case StageStatus.BLOCKED:
            warnings.append(f"{stage.title} is blocked: {stage.summary}")
        case StageStatus.COMPLETE | StageStatus.PENDING | StageStatus.RUNNING:
            pass
        case unreachable:
            assert_never(unreachable)
    match stage.confidence:
        case "low":
            warnings.append(f"{stage.title} has low confidence and needs review.")
        case "high" | "medium" | "unknown":
            pass
        case unreachable:
            assert_never(unreachable)
    if stage.status == StageStatus.COMPLETE and stage.human_approved is not True:
        warnings.append(f"{stage.title} is complete but not human-approved.")
    return warnings


def available_artifact_count(stage: QuestExportStage) -> int:
    if stage.artifact_manifest is None:
        return 0
    return sum(1 for artifact in stage.artifact_manifest.artifacts if artifact.available)


def build_trust_summary(stages: list[QuestExportStage]) -> QuestExportTrustSummary:
    complete_stages = 0
    blocked_stages = 0
    pending_review_stages = 0
    low_confidence_stages = 0
    artifact_available_count = 0
    warnings: list[str] = []
    for stage in stages:
        match stage.status:
            case StageStatus.COMPLETE:
                complete_stages += 1
            case StageStatus.BLOCKED:
                blocked_stages += 1
            case StageStatus.PENDING | StageStatus.RUNNING:
                pass
            case unreachable:
                assert_never(unreachable)
        if stage.status == StageStatus.COMPLETE and stage.human_approved is not True:
            pending_review_stages += 1
        if stage.confidence == "low":
            low_confidence_stages += 1
        artifact_available_count += available_artifact_count(stage)
        warnings.extend(stage_export_warnings(stage))
    return QuestExportTrustSummary(
        artifact_available_count=artifact_available_count,
        blocked_stages=blocked_stages,
        complete_stages=complete_stages,
        low_confidence_stages=low_confidence_stages,
        pending_review_stages=pending_review_stages,
        total_stages=len(stages),
        warnings=warnings,
    )


@router.get("/quests/{quest_id}/export", response_model=QuestExportResponse)
def export_quest(
    quest_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestExportResponse:
    service = QuestService(session)
    try:
        quest = service.get_quest_for_user(quest_id, current_user)
        stages = [quest_export_stage(stage) for stage in service.list_stage_cards(quest.id)]
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return QuestExportResponse(
        generated_at=utc_now().isoformat(),
        quest=quest_export_quest(quest),
        stages=stages,
        trust_summary=build_trust_summary(stages),
    )
