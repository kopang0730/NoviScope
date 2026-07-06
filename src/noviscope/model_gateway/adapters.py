from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Final, Protocol
from urllib.parse import urlparse

import httpx

_PROBE_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
_ANTHROPIC_VERSION: Final = "2023-06-01"
ClientFactory = Callable[[], httpx.Client]


@dataclass(frozen=True, slots=True)
class ModelListProbe:
    base_url: str
    headers: Mapping[str, str]
    model: str
    provider_label: str
    success_message: str


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


def _validate_connection_inputs(base_url: str, api_key: str, model: str) -> str | None:
    scheme = urlparse(base_url).scheme
    if scheme not in {"http", "https"}:
        return "base_url must use http or https"
    if not api_key:
        return "api_key is required"
    if not model:
        return "model is required"
    return None


def _probe_model_list(client_factory: ClientFactory, probe: ModelListProbe) -> tuple[bool, str]:
    try:
        with client_factory() as client:
            response = client.get(_models_url(probe.base_url), headers=probe.headers)
    except httpx.TimeoutException:
        return False, f"Timed out while contacting {probe.provider_label} /models endpoint."
    except httpx.ConnectError:
        return False, f"Could not connect to {probe.provider_label} /models endpoint."
    except httpx.HTTPError as exc:
        return False, f"{probe.provider_label} connection failed: {exc.__class__.__name__}."

    if response.status_code in {401, 403}:
        return False, f"{probe.provider_label} rejected the API key while listing models."
    if response.status_code >= 400:
        return False, f"{probe.provider_label} /models returned HTTP {response.status_code}."

    try:
        model_ids = _model_ids(response.json())
    except ValueError:
        return False, f"{probe.provider_label} /models did not return valid JSON."

    if probe.model not in model_ids:
        return False, f"{probe.provider_label} responded, but the configured model was not listed."
    return True, probe.success_message


class ProviderModelListAdapter:
    provider_label = "Provider"
    success_message = "Connected to provider and confirmed the configured model is available."

    def __init__(self, client_factory: ClientFactory | None = None) -> None:
        self._client_factory = client_factory or self._default_client

    def _default_client(self) -> httpx.Client:
        return httpx.Client(timeout=_PROBE_TIMEOUT, follow_redirects=True)

    def test_connection(self, *, base_url: str, api_key: str, model: str) -> tuple[bool, str]:
        validation_error = _validate_connection_inputs(base_url, api_key, model)
        if validation_error:
            return False, validation_error

        return _probe_model_list(
            self._client_factory,
            ModelListProbe(
                base_url=base_url,
                headers=self._headers(api_key),
                model=model,
                provider_label=self.provider_label,
                success_message=self.success_message,
            ),
        )

    def _headers(self, api_key: str) -> Mapping[str, str]:
        return {"Authorization": f"Bearer {api_key}"}


class OpenAICompatibleAdapter(ProviderModelListAdapter):
    pass


class AnthropicAdapter(ProviderModelListAdapter):
    provider_label = "Anthropic"
    success_message = (
        "Connected to Anthropic provider and confirmed the configured model is available."
    )

    def _headers(self, api_key: str) -> Mapping[str, str]:
        return {"x-api-key": api_key, "anthropic-version": _ANTHROPIC_VERSION}


class ConfigurationOnlyAdapter:
    def __init__(self, provider_label: str) -> None:
        self.provider_label = provider_label

    def test_connection(self, *, base_url: str, api_key: str, model: str) -> tuple[bool, str]:
        validation_error = _validate_connection_inputs(base_url, api_key, model)
        if validation_error:
            return False, validation_error
        return (
            False,
            f"Live connection test is not implemented for {self.provider_label} providers yet.",
        )
