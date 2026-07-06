from collections.abc import Callable
from typing import Protocol
from urllib.parse import urlparse

import httpx

_PROBE_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
ClientFactory = Callable[[], httpx.Client]


class ProviderAdapter(Protocol):
    def test_connection(self, *, base_url: str, api_key: str, model: str) -> tuple[bool, str]:
        """Return connection status and human-readable message."""


def _models_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/models"


def _model_ids(payload) -> set[str]:
    if not isinstance(payload, dict):
        return set()
    data = payload.get("data")
    if not isinstance(data, list):
        return set()
    model_ids: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if isinstance(model_id, str):
            model_ids.add(model_id)
    return model_ids


class OpenAICompatibleAdapter:
    def __init__(self, client_factory: ClientFactory | None = None) -> None:
        self._client_factory = client_factory or self._default_client

    def _default_client(self) -> httpx.Client:
        return httpx.Client(timeout=_PROBE_TIMEOUT, follow_redirects=True)

    def test_connection(self, *, base_url: str, api_key: str, model: str) -> tuple[bool, str]:
        scheme = urlparse(base_url).scheme
        if scheme not in {"http", "https"}:
            return False, "base_url must use http or https"
        if not api_key:
            return False, "api_key is required"
        if not model:
            return False, "model is required"
        try:
            with self._client_factory() as client:
                response = client.get(
                    _models_url(base_url),
                    headers={"Authorization": f"Bearer {api_key}"},
                )
        except httpx.TimeoutException:
            return False, "Timed out while contacting provider /models endpoint."
        except httpx.ConnectError:
            return False, "Could not connect to provider /models endpoint."
        except httpx.HTTPError as exc:
            return False, f"Provider connection failed: {exc.__class__.__name__}."

        if response.status_code in {401, 403}:
            return False, "Provider rejected the API key while listing models."
        if response.status_code >= 400:
            return False, f"Provider /models returned HTTP {response.status_code}."

        try:
            model_ids = _model_ids(response.json())
        except ValueError:
            return False, "Provider /models did not return valid JSON."

        if model not in model_ids:
            return False, "Provider responded, but the configured model was not listed."
        return True, "Connected to provider and confirmed the configured model is available."


class ConfigurationOnlyAdapter:
    def __init__(self, provider_label: str) -> None:
        self.provider_label = provider_label

    def test_connection(self, *, base_url: str, api_key: str, model: str) -> tuple[bool, str]:
        scheme = urlparse(base_url).scheme
        if scheme not in {"http", "https"}:
            return False, "base_url must use http or https"
        if not api_key:
            return False, "api_key is required"
        if not model:
            return False, "model is required"
        return (
            False,
            f"Live connection test is not implemented for {self.provider_label} providers yet.",
        )
