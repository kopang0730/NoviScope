from typing import Protocol
from urllib.parse import urlparse


class ProviderAdapter(Protocol):
    def test_connection(self, *, base_url: str, api_key: str, model: str) -> tuple[bool, str]:
        """Return connection status and human-readable message."""


class EchoAdapter:
    def test_connection(self, *, base_url: str, api_key: str, model: str) -> tuple[bool, str]:
        scheme = urlparse(base_url).scheme
        if scheme not in {"http", "https"}:
            return False, "base_url must use http or https"
        if not api_key:
            return False, "api_key is required"
        if not model:
            return False, "model is required"
        return True, "connection parameters accepted"
