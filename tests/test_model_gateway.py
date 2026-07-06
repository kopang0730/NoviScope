import httpx

from noviscope.model_gateway.adapters import ConfigurationOnlyAdapter, OpenAICompatibleAdapter
from noviscope.model_gateway.service import ModelGateway, ProviderProfile


def test_gateway_registers_and_tests_provider():
    gateway = ModelGateway()
    gateway.register_adapter(
        "openai_compatible",
        OpenAICompatibleAdapter(
            client_factory=lambda: httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                        200,
                        json={"data": [{"id": "example-chat"}]},
                    )
                )
            )
        ),
    )
    profile = ProviderProfile(
        provider_id="provider_1",
        kind="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        default_model="example-chat",
    )

    result = gateway.test_connection(profile)

    assert result.ok is True
    assert result.model == "example-chat"


def test_unknown_provider_kind_fails_connection_test():
    gateway = ModelGateway()
    profile = ProviderProfile(
        provider_id="provider_2",
        kind="missing",
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        default_model="example-chat",
    )

    result = gateway.test_connection(profile)

    assert result.ok is False
    assert "No adapter registered" in result.message


def test_provider_profile_repr_redacts_api_key():
    profile = ProviderProfile(
        provider_id="provider_3",
        kind="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key="sk-secret-value",
        default_model="example-chat",
    )

    assert "sk-secret-value" not in repr(profile)


def test_openai_compatible_adapter_rejects_invalid_url_scheme():
    result = OpenAICompatibleAdapter().test_connection(
        base_url="httpbad://api.example.com",
        api_key="sk-test",
        model="example-chat",
    )

    assert result == (False, "base_url must use http or https")


def test_openai_compatible_adapter_rejects_missing_model_from_models_response():
    adapter = OpenAICompatibleAdapter(
        client_factory=lambda: httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"data": [{"id": "other-chat"}]},
                )
            )
        )
    )

    result = adapter.test_connection(
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        model="example-chat",
    )

    assert result == (
        False,
        "Provider responded, but the configured model was not listed.",
    )


def test_openai_compatible_adapter_reports_api_key_rejection():
    adapter = OpenAICompatibleAdapter(
        client_factory=lambda: httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(401, json={}))
        )
    )

    result = adapter.test_connection(
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        model="example-chat",
    )

    assert result == (False, "Provider rejected the API key while listing models.")


def test_configuration_only_adapter_does_not_claim_live_success():
    result = ConfigurationOnlyAdapter("Anthropic").test_connection(
        base_url="https://api.anthropic.com/v1",
        api_key="sk-test",
        model="claude-sonnet",
    )

    assert result == (
        False,
        "Live connection test is not implemented for Anthropic providers yet.",
    )
