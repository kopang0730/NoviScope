from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, assert_never

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.stage_policy import PAPER_MEETING_WRITER_AGENT_ID
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()


class MarkdownArtifactKey(StrEnum):
    CHINESE_RESEARCH_BRIEF = "chinese_research_brief_markdown"
    ENGLISH_RESEARCH_BRIEF = "english_research_brief_markdown"
    MEETING_OUTLINE = "meeting_outline_markdown"
    IEEE_PAPER_SKELETON = "ieee_paper_skeleton_markdown"


@dataclass(frozen=True, slots=True)
class ArtifactRequestContext:
    session: Session
    current_user: User


@dataclass(frozen=True, slots=True)
class MarkdownArtifact:
    content: str
    filename: str


@dataclass(frozen=True, slots=True)
class MarkdownArtifactUnavailable(Exception):
    status_code: int
    detail: str

    def __str__(self) -> str:
        return self.detail


def get_artifact_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ArtifactRequestContext:
    return ArtifactRequestContext(current_user=current_user, session=session)


def artifact_filename(key: MarkdownArtifactKey) -> str:
    match key:
        case MarkdownArtifactKey.CHINESE_RESEARCH_BRIEF:
            return "noviscope-chinese-research-brief.md"
        case MarkdownArtifactKey.ENGLISH_RESEARCH_BRIEF:
            return "noviscope-english-research-brief.md"
        case MarkdownArtifactKey.MEETING_OUTLINE:
            return "noviscope-meeting-outline.md"
        case MarkdownArtifactKey.IEEE_PAPER_SKELETON:
            return "noviscope-ieee-paper-skeleton.md"
        case unreachable:
            assert_never(unreachable)


def read_markdown_artifact(stage: StageCard, key: MarkdownArtifactKey) -> MarkdownArtifact:
    if stage.agent_id != PAPER_MEETING_WRITER_AGENT_ID:
        raise MarkdownArtifactUnavailable(
            detail="This stage does not expose downloadable Markdown artifacts.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    match stage.status:
        case StageStatus.COMPLETE:
            pass
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            raise MarkdownArtifactUnavailable(
                detail=(
                    "Paper & Meeting Writer must complete before Markdown artifacts can be "
                    "downloaded."
                ),
                status_code=status.HTTP_409_CONFLICT,
            )
        case unreachable:
            assert_never(unreachable)

    content = stage.output_payload.get(key.value)
    if not isinstance(content, str) or not content.strip():
        raise MarkdownArtifactUnavailable(
            detail="The requested Markdown artifact is not available on this stage.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return MarkdownArtifact(content=content, filename=artifact_filename(key))


@router.get("/stages/{stage_id}/artifacts/{artifact_key}/download")
def download_markdown_artifact(
    stage_id: str,
    artifact_key: MarkdownArtifactKey,
    context: Annotated[ArtifactRequestContext, Depends(get_artifact_context)],
) -> Response:
    service = QuestService(context.session)
    try:
        stage = service.get_stage_card_for_user(stage_id, context.current_user)
        artifact = read_markdown_artifact(stage, artifact_key)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except MarkdownArtifactUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return Response(
        content=artifact.content,
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
        media_type="text/markdown; charset=utf-8",
    )
