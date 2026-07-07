from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from noviscope.api.artifacts import (
    MarkdownArtifactManifestResponse,
    build_artifact_manifest,
)
from noviscope.api.dependencies import get_session
from noviscope.api.routes import (
    QuestResponse,
    StageCardResponse,
    quest_response,
    stage_response,
)
from noviscope.api.stage_display_output import (
    StageDisplayOutputResponse,
    build_stage_display_output,
)
from noviscope.api.workflow_canvas import (
    WorkflowCanvasTemplateResponse,
    build_workflow_canvas_template,
)
from noviscope.auth.dependencies import get_current_user
from noviscope.core.stage_policy import PAPER_MEETING_WRITER_AGENT_ID
from noviscope.models.quest import Quest, StageCard
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()


class QuestWorkspaceStageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_manifest: MarkdownArtifactManifestResponse | None
    card: StageCardResponse
    display_output: StageDisplayOutputResponse


class QuestWorkspaceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    canvas_template: WorkflowCanvasTemplateResponse
    quest: QuestResponse
    stages: list[QuestWorkspaceStageResponse]


def artifact_manifest_for_workspace_stage(
    stage: StageCard,
) -> MarkdownArtifactManifestResponse | None:
    if stage.agent_id != PAPER_MEETING_WRITER_AGENT_ID:
        return None
    return build_artifact_manifest(stage)


def workspace_stage_response(stage: StageCard) -> QuestWorkspaceStageResponse:
    return QuestWorkspaceStageResponse(
        artifact_manifest=artifact_manifest_for_workspace_stage(stage),
        card=stage_response(stage),
        display_output=build_stage_display_output(stage),
    )


def build_quest_workspace(quest: Quest, stages: list[StageCard]) -> QuestWorkspaceResponse:
    return QuestWorkspaceResponse(
        canvas_template=build_workflow_canvas_template(),
        quest=quest_response(quest),
        stages=[workspace_stage_response(stage) for stage in stages],
    )


@router.get("/quests/{quest_id}/workspace", response_model=QuestWorkspaceResponse)
def get_quest_workspace(
    quest_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestWorkspaceResponse:
    service = QuestService(session)
    try:
        quest = service.get_quest_for_user(quest_id, current_user)
        stages = service.list_stage_cards(quest.id)
        return build_quest_workspace(quest, stages)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
