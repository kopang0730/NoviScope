from fastapi.testclient import TestClient

from noviscope.main import create_app

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


def register_and_login(client: TestClient, invite_code: str, email: str) -> None:
    invite_response = client.post(
        "/admin/invites",
        headers=DEV_ADMIN_HEADERS,
        json={"code": invite_code, "max_uses": 1},
    )
    assert invite_response.status_code == 201
    register_response = client.post(
        "/auth/register",
        json={
            "display_name": email.split("@")[0],
            "email": email,
            "invite_code": invite_code,
            "password": "password",
        },
    )
    assert register_response.status_code == 201
    login_response = client.post("/auth/login", json={"email": email, "password": "password"})
    assert login_response.status_code == 200


def test_preview_provider_connection_validates_without_saving_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'provider-preview-test.db'}")

    with TestClient(app) as client:
        # Given: a signed-in user preparing a provider config that is not saved yet.
        register_and_login(client, "PROVIDER-PREVIEW", "provider-preview@example.com")

        # When: the user tests the draft provider configuration.
        response = client.post(
            "/provider-tests/preview",
            json={
                "api_key": "sk-preview-secret",
                "base_url": "https://api.example.com/v1",
                "default_model": "example-model",
                "kind": "custom",
            },
        )
        providers_response = client.get("/providers")

    # Then: the test returns a connection result but does not persist the draft.
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "message": "Live connection test is not implemented for custom providers yet.",
        "model": "example-model",
        "ok": False,
        "provider_id": "preview",
    }
    assert "sk-preview-secret" not in str(body)
    assert providers_response.status_code == 200
    assert providers_response.json()["providers"] == []


def test_preview_provider_connection_requires_authentication(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'provider-preview-auth.db'}")

    with TestClient(app) as client:
        response = client.post(
            "/provider-tests/preview",
            json={
                "api_key": "sk-preview-secret",
                "base_url": "https://api.example.com/v1",
                "default_model": "example-model",
                "kind": "custom",
            },
        )

    assert response.status_code == 401
