import json

import httpx
import pytest
from pydantic import SecretStr

from noviscope.agents.provider_chat import (
    ProviderChatClient,
    ProviderChatRequest,
    ProviderChatRunError,
)
from noviscope.models.provider import ProviderApiMode, ProviderKind


def request(api_mode: ProviderApiMode) -> ProviderChatRequest:
    return ProviderChatRequest(
        api_key=SecretStr("test-key"),
        api_mode=api_mode,
        base_url="https://api.example.com/v1",
        messages=[
            {"content": "Return structured JSON.", "role": "system"},
            {"content": "Analyze badminton demand.", "role": "user"},
        ],
        model="research-model",
        provider_kind=ProviderKind.OPENAI_COMPATIBLE,
        temperature=0.2,
    )


def client(handler) -> ProviderChatClient:
    return ProviderChatClient(
        client_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_responses_mode_maps_messages_and_parses_json_output() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.url == httpx.URL("https://api.example.com/v1/responses")
        payload = json.loads(http_request.content)
        assert payload == {
            "input": "Analyze badminton demand.",
            "instructions": "Return structured JSON.",
            "model": "research-model",
            "temperature": 0.2,
        }
        return httpx.Response(
            200,
            json={
                "output": [{
                    "content": [{"text": '{"summary":"Plausible"}', "type": "output_text"}],
                    "type": "message",
                }],
            },
        )

    assert client(handler).complete(request(ProviderApiMode.RESPONSES)) == (
        '{"summary":"Plausible"}'
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"output_text": "partial", "status": "failed"},
        {
            "output": [{
                "content": [{"text": "partial", "type": "output_text"}],
                "status": "incomplete",
                "type": "message",
            }],
            "status": "completed",
        },
    ],
)
def test_responses_mode_rejects_non_completed_json_output(payload: dict) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with pytest.raises(ProviderChatRunError, match="non-completed status"):
        client(handler).complete(request(ProviderApiMode.RESPONSES))


def test_responses_mode_parses_text_event_stream_deltas() -> None:
    first_delta = json.dumps({
        "delta": '{"summary":',
        "type": "response.output_text.delta",
    })
    second_delta = json.dumps({
        "delta": '"Plausible"}',
        "type": "response.output_text.delta",
    })
    stream = "\n".join([
        'event: response.output_text.delta',
        f"data: {first_delta}",
        "",
        'event: response.output_text.delta',
        f"data: {second_delta}",
        "",
        "event: response.completed",
        'data: {"type":"response.completed","response":{"output":[]}}',
        "",
        "data: [DONE]",
        "",
    ])

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=stream,
            headers={"content-type": "text/event-stream"},
        )

    assert client(handler).complete(request(ProviderApiMode.RESPONSES)) == (
        '{"summary":"Plausible"}'
    )


def test_responses_mode_rejects_partial_output_when_stream_fails() -> None:
    stream = "\n".join([
        'data: {"delta":"partial","type":"response.output_text.delta"}',
        "",
        'data: {"type":"response.failed","response":{"error":{"message":"failed"}}}',
        "",
    ])

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=stream,
            headers={"content-type": "text/event-stream"},
        )

    with pytest.raises(ProviderChatRunError, match="reported response.failed"):
        client(handler).complete(request(ProviderApiMode.RESPONSES))


def test_responses_mode_rejects_stream_without_completion() -> None:
    stream = 'data: {"delta":"partial","type":"response.output_text.delta"}\n\n'

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=stream,
            headers={"content-type": "text/event-stream"},
        )

    with pytest.raises(ProviderChatRunError, match="without response.completed"):
        client(handler).complete(request(ProviderApiMode.RESPONSES))


def test_responses_mode_validates_completed_event_before_returning_deltas() -> None:
    stream = "\n".join([
        'data: {"delta":"partial","type":"response.output_text.delta"}',
        "",
        (
            'data: {"type":"response.completed","response":'
            '{"output_text":"partial","status":"failed"}}'
        ),
        "",
    ])

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=stream,
            headers={"content-type": "text/event-stream"},
        )

    with pytest.raises(ProviderChatRunError, match="non-completed status failed"):
        client(handler).complete(request(ProviderApiMode.RESPONSES))


def test_auto_falls_back_to_responses_only_when_chat_endpoint_is_missing() -> None:
    paths: list[str] = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        paths.append(http_request.url.path)
        if http_request.url.path.endswith("/chat/completions"):
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(200, json={"output_text": "Responses result"})

    assert client(handler).complete(request(ProviderApiMode.AUTO)) == "Responses result"
    assert paths == ["/v1/chat/completions", "/v1/responses"]


def test_auto_does_not_hide_chat_authentication_failures() -> None:
    paths: list[str] = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        paths.append(http_request.url.path)
        return httpx.Response(401, json={"error": "unauthorized"})

    with pytest.raises(ProviderChatRunError, match="401"):
        client(handler).complete(request(ProviderApiMode.AUTO))

    assert paths == ["/v1/chat/completions"]


def test_explicit_chat_completions_preserves_existing_endpoint() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.url == httpx.URL(
            "https://api.example.com/v1/chat/completions"
        )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Chat result"}}]},
        )

    assert client(handler).complete(
        request(ProviderApiMode.CHAT_COMPLETIONS)
    ) == "Chat result"


def test_anthropic_missing_endpoint_uses_public_provider_error() -> None:
    base_request = request(ProviderApiMode.AUTO)
    anthropic_request = ProviderChatRequest(
        api_key=base_request.api_key,
        api_mode=base_request.api_mode,
        base_url=base_request.base_url,
        messages=base_request.messages,
        model=base_request.model,
        provider_kind=ProviderKind.ANTHROPIC,
        temperature=base_request.temperature,
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    with pytest.raises(ProviderChatRunError, match="404"):
        client(handler).complete(anthropic_request)
