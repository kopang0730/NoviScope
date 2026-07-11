import httpx
import pytest
from pydantic import SecretStr

from noviscope.agents.provider_chat import (
    ProviderChatClient,
    ProviderChatRequest,
    ProviderChatRunError,
)
from noviscope.models.provider import ProviderKind


def test_provider_chat_error_hides_provider_url_query_secret_when_status_fails() -> None:
    # Given
    url_secret = "sk-url-secret"
    header_secret = "sk-header-secret"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, request=request, json={"error": "invalid api key"})

    client = ProviderChatClient(
        client_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler))
    )

    # When
    with pytest.raises(ProviderChatRunError) as exc_info:
        client.complete(
            ProviderChatRequest(
                api_key=SecretStr(header_secret),
                base_url=f"https://api.example.com/v1?api_key={url_secret}",
                messages=[{"content": "hello", "role": "user"}],
                model="test-model",
                provider_kind=ProviderKind.OPENAI_COMPATIBLE,
                temperature=0.2,
            )
        )

    # Then
    message = str(exc_info.value)
    assert "HTTP 401" in message
    assert url_secret not in message
    assert header_secret not in message
    assert "api_key=" not in message
