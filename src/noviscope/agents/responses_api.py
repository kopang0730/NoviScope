import json
from typing import NotRequired, TypedDict, assert_never

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from noviscope.agents.provider_chat_types import ChatMessage


class ResponsesPayload(TypedDict):
    input: str
    instructions: NotRequired[str]
    model: str
    temperature: float


class ResponsesContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str = ""
    text: str | None = None


class ResponsesOutputItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: list[ResponsesContent] = Field(default_factory=list)
    status: str | None = None


class ResponsesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    output: list[ResponsesOutputItem] = Field(default_factory=list)
    output_text: str | None = None
    status: str | None = None


class ResponsesParseError(ValueError):
    pass


def build_responses_payload(
    messages: list[ChatMessage],
    model: str,
    temperature: float,
) -> ResponsesPayload:
    instructions: list[str] = []
    inputs: list[str] = []
    for message in messages:
        match message["role"]:
            case "system":
                instructions.append(message["content"])
            case "user":
                inputs.append(message["content"])
            case unreachable:
                assert_never(unreachable)

    if not inputs:
        raise ResponsesParseError("Responses API requires at least one user message.")

    payload: ResponsesPayload = {
        "input": "\n\n".join(inputs),
        "model": model,
        "temperature": temperature,
    }
    if instructions:
        payload["instructions"] = "\n\n".join(instructions)
    return payload


def parse_responses_output(response: httpx.Response) -> str:
    content_type = response.headers.get("content-type", "").lower()
    if "text/event-stream" in content_type:
        return _parse_event_stream(response.text)
    try:
        return _parse_response_object(response.json())
    except ResponsesParseError:
        raise
    except (ValueError, ValidationError) as exc:
        raise ResponsesParseError("Invalid Responses API JSON output.") from exc


def _parse_response_object(value: object) -> str:
    response = ResponsesResponse.model_validate(value)
    _validate_response_status(response)
    if response.output_text:
        return response.output_text
    text_parts = [
        content.text
        for output in response.output
        for content in output.content
        if content.text
    ]
    if text_parts:
        return "".join(text_parts)
    raise ResponsesParseError("Responses API returned no text output.")


def _validate_response_status(response: ResponsesResponse) -> None:
    if response.status is not None and response.status != "completed":
        raise ResponsesParseError(
            f"Responses API returned non-completed status {response.status}."
        )
    incomplete_item = next(
        (item for item in response.output if item.status not in {None, "completed"}),
        None,
    )
    if incomplete_item is not None:
        raise ResponsesParseError(
            f"Responses API output item has non-completed status {incomplete_item.status}."
        )


def _parse_event_stream(body: str) -> str:
    deltas: list[str] = []
    completed_response: object | None = None
    completed = False
    for line in body.splitlines():
        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if not data or data == "[DONE]":
            continue
        try:
            event = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ResponsesParseError("Invalid Responses API event stream.") from exc
        if not isinstance(event, dict):
            continue
        event_type = event.get("type")
        if event_type in {"error", "response.failed", "response.incomplete"}:
            raise ResponsesParseError(
                f"Responses API event stream reported {event_type}."
            )
        if event_type == "response.output_text.delta":
            delta = event.get("delta")
            if isinstance(delta, str):
                deltas.append(delta)
        elif event_type == "response.completed":
            completed = True
            completed_response = event.get("response")

    if not completed:
        raise ResponsesParseError(
            "Responses API event stream ended without response.completed."
        )
    if completed_response is not None:
        try:
            completion = ResponsesResponse.model_validate(completed_response)
        except ValidationError as exc:
            raise ResponsesParseError("Invalid completed Responses API event.") from exc
        _validate_response_status(completion)
    if deltas:
        return "".join(deltas)
    if completed_response is not None:
        return _parse_response_object(completed_response)
    raise ResponsesParseError("Responses API event stream returned no text output.")
