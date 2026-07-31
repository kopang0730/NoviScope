from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from typing import Annotated, Final, assert_never
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict
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


MARKDOWN_ARTIFACT_KEYS: Final = (
    MarkdownArtifactKey.CHINESE_RESEARCH_BRIEF,
    MarkdownArtifactKey.ENGLISH_RESEARCH_BRIEF,
    MarkdownArtifactKey.MEETING_OUTLINE,
    MarkdownArtifactKey.IEEE_PAPER_SKELETON,
)
PACKAGE_FILENAME: Final = "noviscope-review-packet.zip"
PACKAGE_MEDIA_TYPE: Final = "application/zip"
MARKDOWN_MEDIA_TYPE: Final = "text/markdown"
STAGE_INCOMPLETE_REASON: Final = (
    "Paper & Meeting Writer must complete before Markdown artifacts can be downloaded."
)


@dataclass(frozen=True, slots=True)
class ArtifactRequestContext:
    session: Session
    current_user: User


@dataclass(frozen=True, slots=True)
class MarkdownArtifact:
    content: str
    filename: str


@dataclass(frozen=True, slots=True)
class MarkdownArtifactPackage:
    content: bytes
    filename: str


@dataclass(frozen=True, slots=True)
class MarkdownArtifactUnavailable(Exception):
    status_code: int
    detail: str

    def __str__(self) -> str:
        return self.detail


class MarkdownArtifactManifestItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: MarkdownArtifactKey
    title: str
    filename: str
    media_type: str
    available: bool
    download_url: str
    missing_reason: str


class MarkdownArtifactManifestResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_id: str
    package_available: bool
    package_download_url: str
    package_filename: str
    package_media_type: str
    package_missing_reason: str
    artifacts: list[MarkdownArtifactManifestItem]


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


def artifact_title(key: MarkdownArtifactKey) -> str:
    match key:
        case MarkdownArtifactKey.CHINESE_RESEARCH_BRIEF:
            return "Chinese research brief"
        case MarkdownArtifactKey.ENGLISH_RESEARCH_BRIEF:
            return "English research brief"
        case MarkdownArtifactKey.MEETING_OUTLINE:
            return "Meeting outline"
        case MarkdownArtifactKey.IEEE_PAPER_SKELETON:
            return "IEEE paper skeleton"
        case unreachable:
            assert_never(unreachable)


def artifact_download_url(stage_id: str, key: MarkdownArtifactKey) -> str:
    return f"/stages/{stage_id}/artifacts/{key.value}/download"


def artifact_package_download_url(stage_id: str) -> str:
    return f"/stages/{stage_id}/artifacts/download"


def ensure_paper_writer_stage(stage: StageCard) -> None:
    if stage.agent_id != PAPER_MEETING_WRITER_AGENT_ID:
        raise MarkdownArtifactUnavailable(
            detail="This stage does not expose downloadable Markdown artifacts.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


def stage_incomplete_reason(stage: StageCard) -> str:
    match stage.status:
        case StageStatus.COMPLETE:
            return ""
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            return STAGE_INCOMPLETE_REASON
        case unreachable:
            assert_never(unreachable)


def artifact_missing_reason(stage: StageCard, key: MarkdownArtifactKey) -> str:
    incomplete_reason = stage_incomplete_reason(stage)
    if incomplete_reason:
        return incomplete_reason

    content = stage.output_payload.get(key.value)
    if not isinstance(content, str) or not content.strip():
        return "The requested Markdown artifact is not available on this stage."
    return ""


def artifact_package_missing_reason(stage: StageCard) -> str:
    for key in MARKDOWN_ARTIFACT_KEYS:
        missing_reason = artifact_missing_reason(stage, key)
        if missing_reason:
            return missing_reason
    return ""


def build_manifest_item(stage: StageCard, key: MarkdownArtifactKey) -> MarkdownArtifactManifestItem:
    missing_reason = artifact_missing_reason(stage, key)
    return MarkdownArtifactManifestItem(
        available=not missing_reason,
        download_url=artifact_download_url(stage.id, key),
        filename=artifact_filename(key),
        key=key,
        media_type=MARKDOWN_MEDIA_TYPE,
        missing_reason=missing_reason,
        title=artifact_title(key),
    )


def build_artifact_manifest(stage: StageCard) -> MarkdownArtifactManifestResponse:
    ensure_paper_writer_stage(stage)
    package_missing_reason = artifact_package_missing_reason(stage)
    return MarkdownArtifactManifestResponse(
        artifacts=[build_manifest_item(stage, key) for key in MARKDOWN_ARTIFACT_KEYS],
        package_available=not package_missing_reason,
        package_download_url=artifact_package_download_url(stage.id),
        package_filename=PACKAGE_FILENAME,
        package_media_type=PACKAGE_MEDIA_TYPE,
        package_missing_reason=package_missing_reason,
        stage_id=stage.id,
    )


def read_markdown_artifact(stage: StageCard, key: MarkdownArtifactKey) -> MarkdownArtifact:
    ensure_paper_writer_stage(stage)
    match stage.status:
        case StageStatus.COMPLETE:
            pass
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            raise MarkdownArtifactUnavailable(
                detail=STAGE_INCOMPLETE_REASON,
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


def build_markdown_artifact_package(stage: StageCard) -> MarkdownArtifactPackage:
    artifacts = [read_markdown_artifact(stage, key) for key in MARKDOWN_ARTIFACT_KEYS]
    with BytesIO() as buffer:
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
            for artifact in artifacts:
                archive.writestr(artifact.filename, artifact.content)
        return MarkdownArtifactPackage(content=buffer.getvalue(), filename=PACKAGE_FILENAME)


@router.get("/stages/{stage_id}/artifacts", response_model=MarkdownArtifactManifestResponse)
def list_markdown_artifacts(
    stage_id: str,
    context: Annotated[ArtifactRequestContext, Depends(get_artifact_context)],
) -> MarkdownArtifactManifestResponse:
    service = QuestService(context.session)
    try:
        stage = service.get_stage_card_for_user(stage_id, context.current_user)
        return build_artifact_manifest(stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except MarkdownArtifactUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/stages/{stage_id}/artifacts/download")
def download_markdown_artifact_package(
    stage_id: str,
    context: Annotated[ArtifactRequestContext, Depends(get_artifact_context)],
) -> Response:
    service = QuestService(context.session)
    try:
        stage = service.get_stage_card_for_user(stage_id, context.current_user)
        artifact_package = build_markdown_artifact_package(stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except MarkdownArtifactUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return Response(
        content=artifact_package.content,
        headers={"Content-Disposition": f'attachment; filename="{artifact_package.filename}"'},
        media_type=PACKAGE_MEDIA_TYPE,
    )


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
