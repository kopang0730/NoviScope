from pydantic import BaseModel, ConfigDict, Field, SecretStr

from noviscope.model_gateway.adapters import ProviderAdapter


class ProviderProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_id: str
    kind: str
    base_url: str
    api_key: SecretStr = Field(repr=False)
    default_model: str


class ConnectionTestResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    provider_id: str
    model: str
    message: str


class ModelGateway:
    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    def register_adapter(self, kind: str, adapter: ProviderAdapter) -> None:
        self._adapters[kind] = adapter

    def test_connection(self, profile: ProviderProfile) -> ConnectionTestResult:
        adapter = self._adapters.get(profile.kind)
        if adapter is None:
            return ConnectionTestResult(
                ok=False,
                provider_id=profile.provider_id,
                model=profile.default_model,
                message=f"No adapter registered for provider kind {profile.kind}",
            )
        ok, message = adapter.test_connection(
            base_url=profile.base_url,
            api_key=profile.api_key.get_secret_value(),
            model=profile.default_model,
        )
        return ConnectionTestResult(
            ok=ok,
            provider_id=profile.provider_id,
            model=profile.default_model,
            message=message,
        )
