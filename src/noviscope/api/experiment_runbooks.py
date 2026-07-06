from dataclasses import dataclass
from typing import Annotated, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import JsonValue
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import EXPERIMENT_PLANNER_AGENT_ID
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

RUNBOOK_FILENAME: Final = "experiment-planner-runbook.md"
RUNBOOK_MEDIA_TYPE: Final = "text/markdown; charset=utf-8"
STAGE_INCOMPLETE_REASON: Final = (
    "Experiment Planner must complete before a runbook can be downloaded."
)
STAGE_UNAVAILABLE_REASON: Final = "This stage does not expose Experiment Planner runbooks."
NOT_AVAILABLE: Final = "_Not available._"
LIST_SECTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("Datasets Needed", "datasets_needed"),
    ("Baselines To Reproduce", "baselines_to_reproduce"),
    ("Metrics", "metrics"),
    ("Ablation Variables", "ablation_variables"),
    ("Expected Tables", "expected_tables"),
    ("Expected Figures", "expected_figures"),
    ("First Runnable Script Plan", "first_runnable_script_plan"),
    ("Failure Risks", "failure_risks"),
    ("Warnings", "warnings"),
)


@dataclass(frozen=True, slots=True)
class RunbookRequestContext:
    session: Session
    current_user: User


@dataclass(frozen=True, slots=True)
class ExperimentRunbook:
    content: str
    filename: str


@dataclass(frozen=True, slots=True)
class ExperimentRunbookUnavailable(Exception):
    status_code: int
    detail: str

    def __str__(self) -> str:
        return self.detail


def get_runbook_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RunbookRequestContext:
    return RunbookRequestContext(current_user=current_user, session=session)


def read_text(payload: JsonObject, key: str) -> str:
    value = payload.get(key)
    match value:
        case str() as text:
            return text.strip()
        case None | bool() | int() | float() | list() | dict():
            return ""
        case unreachable:
            assert_never(unreachable)


def read_text_list(payload: JsonObject, key: str) -> list[str]:
    value = payload.get(key)
    match value:
        case list() as items:
            return read_string_items(items)
        case None | str() | bool() | int() | float() | dict():
            return []
        case unreachable:
            assert_never(unreachable)


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


def read_bool_flag(payload: JsonObject, key: str) -> bool:
    value = payload.get(key)
    match value:
        case bool() as flag:
            return flag
        case None | str() | int() | float() | list() | dict():
            return False
        case unreachable:
            assert_never(unreachable)


def read_source_stage_ids(payload: JsonObject) -> list[str]:
    value = payload.get("source_stage_ids")
    match value:
        case dict() as mapping:
            return [
                f"{stage_name}: {stage_id}"
                for stage_name, stage_id in mapping.items()
                if isinstance(stage_name, str)
                and isinstance(stage_id, str)
                and stage_id.strip()
            ]
        case None | str() | bool() | int() | float() | list():
            return []
        case unreachable:
            assert_never(unreachable)


def markdown_list(values: list[str]) -> str:
    if not values:
        return NOT_AVAILABLE
    return "\n".join(f"- {value}" for value in values)


def markdown_value(value: str) -> str:
    if not value:
        return NOT_AVAILABLE
    return value


def yes_no(value: bool) -> str:
    if value:
        return "yes"
    return "no"


def markdown_section(title: str, body: str) -> list[str]:
    return ["", f"## {title}", "", body]


def ensure_experiment_planner_stage(stage: StageCard) -> None:
    if stage.agent_id != EXPERIMENT_PLANNER_AGENT_ID:
        raise ExperimentRunbookUnavailable(
            detail=STAGE_UNAVAILABLE_REASON,
            status_code=status.HTTP_404_NOT_FOUND,
        )


def ensure_stage_complete(stage: StageCard) -> None:
    match stage.status:
        case StageStatus.COMPLETE:
            return
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            raise ExperimentRunbookUnavailable(
                detail=STAGE_INCOMPLETE_REASON,
                status_code=status.HTTP_409_CONFLICT,
            )
        case unreachable:
            assert_never(unreachable)


def build_experiment_runbook(stage: StageCard) -> ExperimentRunbook:
    ensure_experiment_planner_stage(stage)
    ensure_stage_complete(stage)

    output = stage.output_payload
    evidence = stage.evidence_payload
    lines = [
        "# NoviScope Experiment Runbook",
        "",
        (
            "> Plan-only export. This runbook serializes saved Experiment Planner output "
            "and does not claim experiments have run."
        ),
        *markdown_section(
            "Stage Status",
            "\n".join(
                [
                    f"- Stage ID: `{stage.id}`",
                    f"- Status: `{stage.status.value}`",
                    f"- Confidence: `{markdown_value(read_text(output, 'confidence'))}`",
                    (
                        "- Data availability: "
                        f"`{markdown_value(read_text(output, 'data_availability_status'))}`"
                    ),
                    f"- Human approved: `{yes_no(stage.human_approved is True)}`",
                ]
            ),
        ),
        *markdown_section(
            "Evidence Boundaries",
            "\n".join(
                [
                    f"- Plan only: `{yes_no(read_bool_flag(evidence, 'plan_only'))}`",
                    (
                        "- No experiment results: "
                        f"`{yes_no(read_bool_flag(evidence, 'no_experiment_results'))}`"
                    ),
                    (
                        "- Requires human review: "
                        f"`{yes_no(read_bool_flag(evidence, 'requires_human_review'))}`"
                    ),
                ]
            ),
        ),
        *markdown_section("Summary", markdown_value(stage.summary or read_text(output, "summary"))),
        *markdown_section(
            "Experiment Setup",
            "\n".join(
                [
                    f"- Data path: `{markdown_value(read_text(stage.input_payload, 'data_path'))}`",
                    (
                        "- Code repository: "
                        f"`{markdown_value(read_text(stage.input_payload, 'code_repository'))}`"
                    ),
                    (
                        "- Environment notes: "
                        f"{markdown_value(read_text(stage.input_payload, 'environment_notes'))}"
                    ),
                ]
            ),
        ),
    ]
    for title, key in LIST_SECTIONS:
        lines.extend(markdown_section(title, markdown_list(read_text_list(output, key))))
    lines.extend(
        markdown_section(
            "Compute Requirements",
            markdown_value(read_text(output, "compute_requirements")),
        )
    )
    lines.extend(
        markdown_section(
            "Source Stage IDs",
            markdown_list(read_source_stage_ids(output)),
        )
    )
    lines.append("")
    return ExperimentRunbook(content="\n".join(lines), filename=RUNBOOK_FILENAME)


@router.get("/stages/{stage_id}/experiment-runbook/download")
def download_experiment_runbook(
    stage_id: str,
    context: Annotated[RunbookRequestContext, Depends(get_runbook_context)],
) -> Response:
    service = QuestService(context.session)
    try:
        stage = service.get_stage_card_for_user(stage_id, context.current_user)
        runbook = build_experiment_runbook(stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ExperimentRunbookUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return Response(
        content=runbook.content,
        headers={"Content-Disposition": f'attachment; filename="{runbook.filename}"'},
        media_type=RUNBOOK_MEDIA_TYPE,
    )
