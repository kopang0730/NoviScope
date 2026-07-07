from typing import Annotated, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import JsonValue
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.api.stage_display_output import sanitize_json_value
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    EXPERIMENT_PLANNER_AGENT_ID,
    normalize_stage_output_payload,
    stage_confidence,
)
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

RUNBOOK_FILENAME: Final = "experiment-planner-runbook.md"
RUNBOOK_MEDIA_TYPE: Final = "text/markdown; charset=utf-8"
RUNBOOK_NOTE: Final = (
    "Plan-only export. This runbook serializes saved Experiment Planner output "
    "and does not claim experiments have run."
)
STAGE_INCOMPLETE_REASON: Final = (
    "Experiment Planner must complete before a runbook can be downloaded."
)
STAGE_UNAVAILABLE_REASON: Final = "This stage does not expose Experiment Planner runbooks."
NOT_AVAILABLE: Final = "_Not available._"
LIST_FIELDS: Final[tuple[tuple[str, str], ...]] = (
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


def sanitized_payload(payload: JsonObject, root_path: str) -> tuple[JsonObject, int]:
    sanitized = sanitize_json_value(payload, root_path)
    match sanitized.value:
        case dict() as value:
            return value, len(sanitized.hidden_fields)
        case None | bool() | int() | float() | str() | list():
            return {}, len(sanitized.hidden_fields)
        case unreachable:
            assert_never(unreachable)


def text_value(payload: JsonObject, key: str) -> str:
    value: JsonValue | None = payload.get(key)
    match value:
        case str() as text:
            return text.strip()
        case None | bool() | int() | float() | list() | dict():
            return ""
        case unreachable:
            assert_never(unreachable)


def boolean_label(payload: JsonObject, key: str) -> str:
    value: JsonValue | None = payload.get(key)
    match value:
        case True:
            return "yes"
        case False:
            return "no"
        case None | str() | int() | float() | list() | dict():
            return "not recorded"
        case unreachable:
            assert_never(unreachable)


def text_list(payload: JsonObject, key: str) -> list[str]:
    value: JsonValue | None = payload.get(key)
    match value:
        case list() as items:
            return string_items(items)
        case None | str() | bool() | int() | float() | dict():
            return []
        case unreachable:
            assert_never(unreachable)


def string_items(items: list[JsonValue]) -> list[str]:
    values: list[str] = []
    for item in items:
        match item:
            case str() as text:
                stripped = text.strip()
                if stripped:
                    values.append(stripped)
            case None | bool() | int() | float() | list() | dict():
                pass
            case unreachable:
                assert_never(unreachable)
    return values


def source_stage_items(payload: JsonObject) -> list[str]:
    value: JsonValue | None = payload.get("source_stage_ids")
    match value:
        case dict() as mapping:
            items: list[str] = []
            for stage_name, stage_id in mapping.items():
                match stage_id:
                    case str() as text:
                        stripped = text.strip()
                        if stripped:
                            items.append(f"{stage_name}: {stripped}")
                    case None | bool() | int() | float() | list() | dict():
                        pass
                    case unreachable:
                        assert_never(unreachable)
            return items
        case None | str() | bool() | int() | float() | list():
            return []
        case unreachable:
            assert_never(unreachable)


def markdown_value(value: str) -> str:
    return value or NOT_AVAILABLE


def markdown_list(values: list[str]) -> str:
    if not values:
        return NOT_AVAILABLE
    return "\n".join(f"- {value}" for value in values)


def section(title: str, body: str) -> list[str]:
    return ["", f"## {title}", "", body]


def human_review_label(stage: StageCard) -> str:
    match stage.human_approved:
        case True:
            return "approved"
        case False:
            return "rejected"
        case None:
            return "pending review"
        case unreachable:
            assert_never(unreachable)


def assert_runbook_available(stage: StageCard) -> None:
    if stage.agent_id != EXPERIMENT_PLANNER_AGENT_ID:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=STAGE_UNAVAILABLE_REASON,
        )
    match stage.status:
        case StageStatus.COMPLETE:
            return
        case StageStatus.PENDING | StageStatus.RUNNING | StageStatus.BLOCKED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=STAGE_INCOMPLETE_REASON,
            )
        case unreachable:
            assert_never(unreachable)


def runbook_stage_status(stage: StageCard, output: JsonObject) -> str:
    data_availability = markdown_value(text_value(output, "data_availability_status"))
    return "\n".join(
        [
            f"- Stage ID: `{stage.id}`",
            f"- Status: `{stage.status.value}`",
            f"- Confidence: `{stage_confidence(stage.agent_id, output)}`",
            f"- Data availability: `{data_availability}`",
            f"- Human review: `{human_review_label(stage)}`",
        ]
    )


def runbook_evidence_boundaries(evidence: JsonObject) -> str:
    return "\n".join(
        [
            f"- Plan only: `{boolean_label(evidence, 'plan_only')}`",
            f"- No experiment results: `{boolean_label(evidence, 'no_experiment_results')}`",
            f"- Requires human review: `{boolean_label(evidence, 'requires_human_review')}`",
        ]
    )


def runbook_setup(input_payload: JsonObject) -> str:
    environment_notes = markdown_value(text_value(input_payload, "environment_notes"))
    return "\n".join(
        [
            f"- Data path: `{markdown_value(text_value(input_payload, 'data_path'))}`",
            f"- Code repository: `{markdown_value(text_value(input_payload, 'code_repository'))}`",
            f"- Environment notes: {environment_notes}",
        ]
    )


def build_experiment_runbook(stage: StageCard) -> str:
    assert_runbook_available(stage)
    output_payload = normalize_stage_output_payload(stage.agent_id, stage.output_payload)
    output, output_hidden = sanitized_payload(output_payload, "output_payload")
    evidence, evidence_hidden = sanitized_payload(stage.evidence_payload, "evidence_payload")
    input_payload, input_hidden = sanitized_payload(stage.input_payload, "input_payload")
    hidden_count = output_hidden + evidence_hidden + input_hidden
    lines = [
        "# NoviScope Experiment Runbook",
        "",
        f"> {RUNBOOK_NOTE}",
        *section("Stage Status", runbook_stage_status(stage, output)),
        *section("Evidence Boundaries", runbook_evidence_boundaries(evidence)),
        *section("Summary", markdown_value(stage.summary or text_value(output, "summary"))),
        *section("Experiment Setup", runbook_setup(input_payload)),
    ]
    for title, key in LIST_FIELDS:
        lines.extend(section(title, markdown_list(text_list(output, key))))
    lines.extend(
        section("Compute Requirements", markdown_value(text_value(output, "compute_requirements")))
    )
    lines.extend(section("Source Stage IDs", markdown_list(source_stage_items(output))))
    if hidden_count:
        lines.extend(section("Hidden Payload Fields", f"{hidden_count} field(s) omitted"))
    lines.extend(["", "---", "", "Generated by NoviScope from saved Experiment Planner state."])
    return "\n".join(lines) + "\n"


@router.get("/stages/{stage_id}/experiment-runbook/download")
def download_experiment_runbook(
    stage_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    service = QuestService(session)
    try:
        stage = service.get_stage_card_for_user(stage_id, current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return Response(
        content=build_experiment_runbook(stage),
        headers={"Content-Disposition": f'attachment; filename="{RUNBOOK_FILENAME}"'},
        media_type=RUNBOOK_MEDIA_TYPE,
    )
