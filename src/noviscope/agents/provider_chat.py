from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, Literal, NotRequired, TypedDict, assert_never

import httpx
from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError

from noviscope.agents.provider_chat_types import ChatMessage
from noviscope.agents.responses_api import (
    ResponsesParseError,
    ResponsesPayload,
    build_responses_payload,
    parse_responses_output,
)
from noviscope.models.provider import ProviderApiMode, ProviderKind

ANTHROPIC_API_VERSION: Final = "2023-06-01"
DEFAULT_MAX_TOKENS: Final = 2048
_MODEL_REQUEST_TIMEOUT: Final = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

ClientFactory = Callable[[], httpx.Client]


@dataclass(frozen=True, slots=True)
class ProviderChatRunError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


class ChatCompletionPayload(TypedDict):
    model: str
    messages: list[ChatMessage]
    temperature: float


class AnthropicMessage(TypedDict):
    role: Literal["user"]
    content: str


class AnthropicMessagesPayload(TypedDict):
    model: str
    max_tokens: int
    messages: list[AnthropicMessage]
    system: NotRequired[str]


@dataclass(frozen=True, slots=True)
class ProviderChatRequest:
    provider_kind: ProviderKind
    base_url: str
    model: str
    api_key: SecretStr
    messages: list[ChatMessage]
    temperature: float
    api_mode: ProviderApiMode = ProviderApiMode.AUTO


class ChatCompletionMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str


class ChatCompletionChoice(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: ChatCompletionMessage


class ChatCompletionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    choices: list[ChatCompletionChoice]


class AnthropicContentBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str
    text: str | None = None


class AnthropicMessagesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: list[AnthropicContentBlock]


class _ProviderEndpointUnavailable(Exception):
    def __init__(self, endpoint: str, status_code: int) -> None:
        super().__init__(endpoint, status_code)
        self.endpoint = endpoint
        self.status_code = status_code


class ProviderChatClient:
    def __init__(self, client_factory: ClientFactory | None = None) -> None:
        self._client_factory = client_factory or self._default_client

    def complete(self, request: ProviderChatRequest) -> str:
        try:
            match request.provider_kind:
                case ProviderKind.OPENAI_COMPATIBLE | ProviderKind.CUSTOM:
                    return self._complete_openai_compatible(request)
                case ProviderKind.ANTHROPIC:
                    return self._complete_anthropic(request)
                case unreachable:
                    assert_never(unreachable)
        except _ProviderEndpointUnavailable as exc:
            raise ProviderChatRunError(
                f"Model provider endpoint unavailable ({exc.status_code}): {exc.endpoint}"
            ) from exc

    def _default_client(self) -> httpx.Client:
        return httpx.Client(timeout=_MODEL_REQUEST_TIMEOUT, follow_redirects=True)

    def _complete_openai_compatible(self, request: ProviderChatRequest) -> str:
        match request.api_mode:
            case ProviderApiMode.AUTO:
                try:
                    return self._complete_chat_completions(request)
                except _ProviderEndpointUnavailable:
                    return self._complete_responses(request)
            case ProviderApiMode.CHAT_COMPLETIONS:
                return self._complete_chat_completions(request)
            case ProviderApiMode.RESPONSES:
                return self._complete_responses(request)
            case unreachable:
                assert_never(unreachable)

    def _complete_chat_completions(self, request: ProviderChatRequest) -> str:
        endpoint = f"{request.base_url.rstrip('/')}/chat/completions"
        payload: ChatCompletionPayload = {
            "messages": request.messages,
            "model": request.model,
            "temperature": request.temperature,
        }
        headers = {
            "Authorization": f"Bearer {request.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

        response = self._post_json(endpoint, payload, headers)
        try:
            completion = ChatCompletionResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise ProviderChatRunError(
                "Model provider returned an invalid chat completion response."
            ) from exc
        if not completion.choices:
            raise ProviderChatRunError("Model provider returned no choices.")
        return completion.choices[0].message.content

    def _complete_responses(self, request: ProviderChatRequest) -> str:
        endpoint = f"{request.base_url.rstrip('/')}/responses"
        payload = build_responses_payload(
            request.messages,
            request.model,
            request.temperature,
        )
        headers = {
            "Authorization": f"Bearer {request.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        response = self._post_json(endpoint, payload, headers)
        try:
            return parse_responses_output(response)
        except ResponsesParseError as exc:
            raise ProviderChatRunError(str(exc)) from exc

    def _complete_anthropic(self, request: ProviderChatRequest) -> str:
        endpoint = f"{request.base_url.rstrip('/')}/messages"
        payload = build_anthropic_messages_payload(request)
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": ANTHROPIC_API_VERSION,
            "x-api-key": request.api_key.get_secret_value(),
        }

        response = self._post_json(endpoint, payload, headers)
        try:
            message = AnthropicMessagesResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise ProviderChatRunError(
                "Anthropic provider returned an invalid messages response."
            ) from exc

        for block in message.content:
            match block.type:
                case "text" if block.text:
                    return block.text
                case _:
                    continue
        raise ProviderChatRunError("Anthropic provider returned no text content.")

    def _post_json(
        self,
        endpoint: str,
        payload: ChatCompletionPayload | AnthropicMessagesPayload | ResponsesPayload,
        headers: dict[str, str],
    ) -> httpx.Response:
        try:
            with self._client_factory() as client:
                response = client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {404, 405}:
                raise _ProviderEndpointUnavailable(
                    endpoint=endpoint,
                    status_code=exc.response.status_code,
                ) from exc
            raise ProviderChatRunError(f"Model provider request failed: {exc}") from exc
        except httpx.HTTPError as exc:
            raise ProviderChatRunError(f"Model provider request failed: {exc}") from exc
        return response


def build_anthropic_messages_payload(request: ProviderChatRequest) -> AnthropicMessagesPayload:
    system_prompt_parts: list[str] = []
    messages: list[AnthropicMessage] = []
    for message in request.messages:
        match message["role"]:
            case "system":
                system_prompt_parts.append(message["content"])
            case "user":
                messages.append({"content": message["content"], "role": "user"})
            case unreachable:
                assert_never(unreachable)

    if not messages:
        raise ProviderChatRunError("Anthropic provider requires at least one user message.")

    payload: AnthropicMessagesPayload = {
        "max_tokens": DEFAULT_MAX_TOKENS,
        "messages": messages,
        "model": request.model,
    }
    if system_prompt_parts:
        payload["system"] = "\n\n".join(system_prompt_parts)
    return payload
