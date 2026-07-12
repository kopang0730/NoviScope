import json
from dataclasses import dataclass
from typing import Annotated, Final, assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import get_current_user
from noviscope.core.stage_policy import normalize_stage_output_payload
from noviscope.models.quest import StageCard
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()

OUTPUT_PAYLOAD_ROOT: Final = "output_payload"
RAW_RESPONSE_FIELD: Final = "raw_response"


class StageRawResponseItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    content: JsonValue
    char_count: int


class StageRawResponseResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage_id: str
    agent_id: str
    stage_title: str
    raw_response_count: int
    raw_responses: list[StageRawResponseItem]


@dataclass(frozen=True, slots=True)
class StageRawResponseContext:
    session: Session
    current_user: User


def get_stage_raw_response_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StageRawResponseContext:
    return StageRawResponseContext(current_user=current_user, session=session)


def json_value_char_count(value: JsonValue) -> int:
    match value:
        case str() as text:
            return len(text)
        case None | bool() | int() | float() | list() | dict():
            compact_json = json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            return len(compact_json)
        case unreachable:
            assert_never(unreachable)


def collect_raw_responses(value: JsonValue, parent_path: str) -> list[StageRawResponseItem]:
    match value:
        case dict() as mapping:
            raw_responses: list[StageRawResponseItem] = []
            for field_name, item in mapping.items():
                child_path = f"{parent_path}.{field_name}"
                if field_name == RAW_RESPONSE_FIELD:
                    raw_responses.append(
                        StageRawResponseItem(
                            char_count=json_value_char_count(item),
                            content=item,
                            path=child_path,
                        )
                    )
                    continue
                raw_responses.extend(collect_raw_responses(item, child_path))
            return raw_responses
        case list() as items:
            raw_responses: list[StageRawResponseItem] = []
            for index, item in enumerate(items):
                raw_responses.extend(collect_raw_responses(item, f"{parent_path}[{index}]"))
            return raw_responses
        case None | str() | bool() | int() | float():
            return []
        case unreachable:
            assert_never(unreachable)


def build_stage_raw_response(stage: StageCard) -> StageRawResponseResponse:
    output_payload = normalize_stage_output_payload(stage.agent_id, stage.output_payload)
    raw_responses = collect_raw_responses(output_payload, OUTPUT_PAYLOAD_ROOT)
    return StageRawResponseResponse(
        agent_id=stage.agent_id,
        raw_response_count=len(raw_responses),
        raw_responses=raw_responses,
        stage_id=stage.id,
        stage_title=stage.title,
    )


@router.get("/stages/{stage_id}/raw-response", response_model=StageRawResponseResponse)
def get_stage_raw_response(
    stage_id: str,
    context: Annotated[
        StageRawResponseContext,
        Depends(get_stage_raw_response_context),
    ],
) -> StageRawResponseResponse:
    service = QuestService(context.session)
    try:
        stage = service.get_stage_card_for_user(stage_id, context.current_user)
        return build_stage_raw_response(stage)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
