from dataclasses import dataclass
from typing import Annotated, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import JsonValue
from sqlmodel import Session

from noviscope.api.artifacts import MarkdownArtifactKey
from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.stage_policy import PAPER_MEETING_WRITER_AGENT_ID
from noviscope.models.common import utc_now
from noviscope.models.quest import Quest, StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

BUNDLE_FILENAME: Final = "noviscope-research-brief-bundle.md"
BUNDLE_MEDIA_TYPE: Final = "text/markdown; charset=utf-8"
PAPER_WRITER_INCOMPLETE_REASON: Final = (
    "Paper & Meeting Writer must complete before the research brief bundle can be downloaded."
)
SOURCE_STAGE_ORDER: Final = (
    "demand_validation", "literature_scout", "idea_generator", "experiment_planner"
)


@dataclass(frozen=True, slots=True)
class ResearchBundleContext:
    session: Session
    current_user: User


@dataclass(frozen=True, slots=True)
class ResearchBundleUnavailable(Exception):
    status_code: int
    detail: str

    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True)
class ResearchBundleArtifactContent:
    chinese_research_brief: str
    english_research_brief: str
    meeting_outline: str
    ieee_paper_skeleton: str


def get_research_bundle_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResearchBundleContext:
    return ResearchBundleContext(current_user=current_user, session=session)


def paper_writer_stage(stages: list[StageCard]) -> StageCard:
    for stage in stages:
        if stage.agent_id == PAPER_MEETING_WRITER_AGENT_ID:
            return stage
    raise ResearchBundleUnavailable(
        detail="Paper & Meeting Writer stage was not found for this quest.",
        status_code=status.HTTP_404_NOT_FOUND,
    )


def require_complete_paper_writer(stage: StageCard) -> None:
    match stage.status:
        case StageStatus.COMPLETE:
            return
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            raise ResearchBundleUnavailable(
                detail=PAPER_WRITER_INCOMPLETE_REASON,
                status_code=status.HTTP_409_CONFLICT,
            )
        case unreachable:
            assert_never(unreachable)


def markdown_section_title(key: MarkdownArtifactKey) -> str:
    match key:
        case MarkdownArtifactKey.CHINESE_RESEARCH_BRIEF:
            return "Chinese Research Brief"
        case MarkdownArtifactKey.ENGLISH_RESEARCH_BRIEF:
            return "English Research Brief"
        case MarkdownArtifactKey.MEETING_OUTLINE:
            return "Meeting Outline"
        case MarkdownArtifactKey.IEEE_PAPER_SKELETON:
            return "IEEE Paper Skeleton"
        case unreachable:
            assert_never(unreachable)


def required_markdown(stage: StageCard, key: MarkdownArtifactKey) -> str:
    value = stage.output_payload.get(key.value)
    match value:
        case str() as text if text.strip():
            return text.strip()
        case None | str() | bool() | int() | float() | list() | dict():
            raise ResearchBundleUnavailable(
                detail=f"{markdown_section_title(key)} is not available on this stage.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        case unreachable:
            assert_never(unreachable)


def artifact_content(stage: StageCard) -> ResearchBundleArtifactContent:
    return ResearchBundleArtifactContent(
        chinese_research_brief=required_markdown(
            stage,
            MarkdownArtifactKey.CHINESE_RESEARCH_BRIEF,
        ),
        english_research_brief=required_markdown(
            stage,
            MarkdownArtifactKey.ENGLISH_RESEARCH_BRIEF,
        ),
        ieee_paper_skeleton=required_markdown(
            stage,
            MarkdownArtifactKey.IEEE_PAPER_SKELETON,
        ),
        meeting_outline=required_markdown(stage, MarkdownArtifactKey.MEETING_OUTLINE),
    )


def text_or_missing(value: JsonValue | None) -> str:
    match value:
        case str() as text if text.strip():
            return text.strip()
        case None | str() | bool() | int() | float() | list() | dict():
            return "missing"
        case unreachable:
            assert_never(unreachable)


def render_source_stage_ids(value: JsonValue | None) -> str:
    match value:
        case dict() as mapping:
            return "\n".join(
                f"- {stage_key}: {text_or_missing(mapping.get(stage_key))}"
                for stage_key in SOURCE_STAGE_ORDER
            )
        case None | str() | bool() | int() | float() | list():
            return "\n".join(f"- {stage_key}: missing" for stage_key in SOURCE_STAGE_ORDER)
        case unreachable:
            assert_never(unreachable)


def render_bullet_list(value: JsonValue | None) -> str:
    match value:
        case list() as items:
            lines: list[str] = []
            for item in items:
                match item:
                    case str() as text if text.strip():
                        lines.append(f"- {text.strip()}")
                    case None | str() | bool() | int() | float() | list() | dict():
                        pass
                    case unreachable:
                        assert_never(unreachable)
            return "\n".join(lines) if lines else "- None recorded."
        case None | str() | bool() | int() | float() | dict():
            return "- None recorded."
        case unreachable:
            assert_never(unreachable)


def human_approval_label(value: bool | None) -> str:
    match value:
        case True:
            return "Yes"
        case False | None:
            return "No"
        case unreachable:
            assert_never(unreachable)


def render_research_bundle(quest: Quest, stage: StageCard) -> str:
    content = artifact_content(stage)
    output_payload = stage.output_payload
    return "\n\n".join(
        [
            "# NoviScope Research Brief Bundle",
            f"Generated at: {utc_now().isoformat()}",
            f"Quest: {quest.title}",
            f"Initial direction: {quest.initial_direction}",
            "## Trust & Review Status\n"
            f"- Paper writer stage: {stage.status.value}\n"
            f"- Confidence: {text_or_missing(output_payload.get('confidence'))}\n"
            f"- Human approved: {human_approval_label(stage.human_approved)}\n"
            f"- Stage summary: {stage.summary}",
            "## Source Stage IDs\n"
            + render_source_stage_ids(output_payload.get("source_stage_ids")),
            "## Verified Facts\n" + render_bullet_list(output_payload.get("verified_facts")),
            "## Model-Generated Hypotheses\n"
            + render_bullet_list(output_payload.get("model_generated_hypotheses")),
            "## Human Review Required\n"
            + render_bullet_list(output_payload.get("human_review_required")),
            "## Experiment Results Status\n"
            + render_bullet_list(output_payload.get("experiment_results_not_available")),
            "## Warnings\n" + render_bullet_list(output_payload.get("warnings")),
            "## Chinese Research Brief\n" + content.chinese_research_brief,
            "## English Research Brief\n" + content.english_research_brief,
            "## Meeting Outline\n" + content.meeting_outline,
            "## IEEE Paper Skeleton\n" + content.ieee_paper_skeleton,
        ]
    )


@router.get("/quests/{quest_id}/research-brief/download")
def download_research_brief_bundle(
    quest_id: str,
    context: Annotated[ResearchBundleContext, Depends(get_research_bundle_context)],
) -> Response:
    service = QuestService(context.session)
    try:
        quest = service.get_quest_for_user(quest_id, context.current_user)
        stage = paper_writer_stage(service.list_stage_cards(quest.id))
        require_complete_paper_writer(stage)
        markdown = render_research_bundle(quest, stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ResearchBundleUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return Response(
        content=markdown,
        headers={"Content-Disposition": f'attachment; filename="{BUNDLE_FILENAME}"'},
        media_type=BUNDLE_MEDIA_TYPE,
    )
