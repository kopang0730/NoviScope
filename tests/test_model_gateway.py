from noviscope.model_gateway.adapters import EchoAdapter
from noviscope.model_gateway.service import ModelGateway, ProviderProfile


def test_gateway_registers_and_tests_provider():
    gateway = ModelGateway()
    gateway.register_adapter("openai_compatible", EchoAdapter())
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


def test_echo_adapter_rejects_invalid_url_scheme():
    result = EchoAdapter().test_connection(
        base_url="httpbad://api.example.com",
        api_key="sk-test",
        model="example-chat",
    )

    assert result == (False, "base_url must use http or https")
