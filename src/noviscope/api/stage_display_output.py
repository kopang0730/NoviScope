from dataclasses import dataclass
from typing import Annotated, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    StageConfidence,
    normalize_stage_output_payload,
    stage_confidence,
)
from noviscope.models.quest import StageCard, StageStatus
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

OUTPUT_PAYLOAD_ROOT: Final = "output_payload"
HIDDEN_DISPLAY_KEYS: Final = frozenset(
    {
        "api_key",
        "raw_response",
        "secret",
    }
)
HIDDEN_DISPLAY_KEY_MARKERS: Final = frozenset(
    {
        "api_key",
        "ciphertext",
        "raw_response",
        "secret",
    }
)


class StageDisplayOutputResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_id: str
    agent_id: str
    status: StageStatus
    confidence: StageConfidence
    summary: str
    output_available: bool
    raw_response_available: bool
    display_payload: JsonObject
    hidden_fields: list[str]


@dataclass(frozen=True, slots=True)
class StageDisplayOutputContext:
    session: Session
    current_user: User


@dataclass(frozen=True, slots=True)
class SanitizedJsonValue:
    value: JsonValue
    hidden_fields: list[str]


def get_stage_display_output_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StageDisplayOutputContext:
    return StageDisplayOutputContext(current_user=current_user, session=session)


def json_path(parent_path: str, child_name: str) -> str:
    return f"{parent_path}.{child_name}"


def should_hide_display_field(field_name: str) -> bool:
    normalized = field_name.lower()
    return (
        normalized.endswith("token")
        or normalized in HIDDEN_DISPLAY_KEYS
        or any(marker in normalized for marker in HIDDEN_DISPLAY_KEY_MARKERS)
    )


def sanitize_json_value(value: JsonValue, parent_path: str) -> SanitizedJsonValue:
    match value:
        case dict() as mapping:
            sanitized: JsonObject = {}
            hidden_fields: list[str] = []
            for field_name, item in mapping.items():
                child_path = json_path(parent_path, field_name)
                if should_hide_display_field(field_name):
                    hidden_fields.append(child_path)
                    continue
                child = sanitize_json_value(item, child_path)
                sanitized[field_name] = child.value
                hidden_fields.extend(child.hidden_fields)
            return SanitizedJsonValue(hidden_fields=hidden_fields, value=sanitized)
        case list() as items:
            sanitized_items: list[JsonValue] = []
            hidden_fields = []
            for index, item in enumerate(items):
                child = sanitize_json_value(item, f"{parent_path}[{index}]")
                sanitized_items.append(child.value)
                hidden_fields.extend(child.hidden_fields)
            return SanitizedJsonValue(hidden_fields=hidden_fields, value=sanitized_items)
        case None | str() | bool() | int() | float():
            return SanitizedJsonValue(hidden_fields=[], value=value)
        case unreachable:
            assert_never(unreachable)


def build_stage_display_output(stage: StageCard) -> StageDisplayOutputResponse:
    output_payload = normalize_stage_output_payload(stage.agent_id, stage.output_payload)
    sanitized = sanitize_json_value(output_payload, OUTPUT_PAYLOAD_ROOT)
    match sanitized.value:
        case dict() as display_payload:
            sanitized_payload = display_payload
        case None | str() | bool() | int() | float() | list():
            sanitized_payload = {}
        case unreachable:
            assert_never(unreachable)
    return StageDisplayOutputResponse(
        agent_id=stage.agent_id,
        confidence=stage_confidence(stage.agent_id, output_payload),
        display_payload=sanitized_payload,
        hidden_fields=sanitized.hidden_fields,
        output_available=bool(output_payload),
        raw_response_available=any(
            hidden_field.endswith(".raw_response") for hidden_field in sanitized.hidden_fields
        ),
        stage_id=stage.id,
        status=stage.status,
        summary=stage.summary,
    )


@router.get("/stages/{stage_id}/display-output", response_model=StageDisplayOutputResponse)
def get_stage_display_output(
    stage_id: str,
    context: Annotated[
        StageDisplayOutputContext,
        Depends(get_stage_display_output_context),
    ],
) -> StageDisplayOutputResponse:
    service = QuestService(context.session)
    try:
        stage = service.get_stage_card_for_user(stage_id, context.current_user)
        return build_stage_display_output(stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
