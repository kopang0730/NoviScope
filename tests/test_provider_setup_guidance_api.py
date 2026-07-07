from fastapi.testclient import TestClient
from sqlmodel import Session, select

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import DEMAND_VALIDATOR_AGENT_ID
from noviscope.db.session import create_db_engine
from noviscope.main import create_app
from noviscope.models.user import User, UserRole

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


def promote_user_to_admin(database_url: str, email: str) -> None:
    engine = create_db_engine(database_url)
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).one()
        user.role = UserRole.ADMIN
        session.add(user)
        session.commit()


def create_stage_id(client: TestClient, agent_id: str) -> str:
    quest_response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision for badminton action recognition.",
            "title": "Badminton action recognition",
        },
    )
    assert quest_response.status_code == 201
    stages_response = client.get(f"/quests/{quest_response.json()['id']}/stages")
    assert stages_response.status_code == 200
    stages = stages_response.json()["stages"]
    return next(stage["id"] for stage in stages if stage["agent_id"] == agent_id)


def create_provider(client: TestClient, name: str, scope: str = "personal") -> JsonObject:
    response = client.post(
        "/providers",
        json={
            "api_key": f"{name}-key",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4.1-mini",
            "kind": "openai_compatible",
            "name": name,
            "scope": scope,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_provider_setup_guidance_blocks_missing_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'provider-guidance-missing.db'}")

    with TestClient(app) as client:
        register_and_login(client, "GUIDE-MISSING", "guide-missing@example.com")
        stage_id = create_stage_id(client, DEMAND_VALIDATOR_AGENT_ID)

        response = client.get(f"/stages/{stage_id}/provider-setup-guidance")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_status"] == "blocked"
    assert body["reason"] == "missing_provider"
    assert body["can_run"] is False
    assert body["setup_actions"] == [
        "Create a personal provider or ask an admin to configure a shared provider.",
        "Set the provider base URL, model, and API key.",
        "Keep the provider active before running this stage.",
    ]
    assert "api_key" not in str(body)


def test_provider_setup_guidance_reports_auto_selected_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'provider-guidance-ready.db'}")

    with TestClient(app) as client:
        register_and_login(client, "GUIDE-READY", "guide-ready@example.com")
        provider = create_provider(client, "ready-openai")
        stage_id = create_stage_id(client, DEMAND_VALIDATOR_AGENT_ID)

        response = client.get(f"/stages/{stage_id}/provider-setup-guidance")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_status"] == "ready"
    assert body["reason"] == "auto_select_ready"
    assert body["can_run"] is True
    assert body["provider_id"] == provider["id"]
    assert body["provider_model"] == "gpt-4.1-mini"
    assert body["provider_source"] == "auto_select"
    assert body["setup_actions"] == []
    assert "ready-openai-key" not in str(body)


def test_provider_setup_guidance_reports_server_managed_literature_scout(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'provider-guidance-server.db'}")

    with TestClient(app) as client:
        register_and_login(client, "GUIDE-SERVER", "guide-server@example.com")
        stage_id = create_stage_id(client, LITERATURE_SCOUT_AGENT_ID)

        response = client.get(f"/stages/{stage_id}/provider-setup-guidance")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_status"] == "server_managed"
    assert body["reason"] == "server_managed"
    assert body["can_run"] is True
    assert body["provider_name"] == "OpenAlex"
    assert body["provider_model"] == "openalex-works"
    assert body["uses_server_managed_provider"] is True
    assert body["setup_actions"] == []


def test_provider_setup_guidance_reports_inactive_assigned_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'provider-guidance-inactive.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        register_and_login(client, "GUIDE-ADMIN", "guide-admin@example.com")
        promote_user_to_admin(database_url, "guide-admin@example.com")
        provider = create_provider(client, "inactive-shared", "shared")
        inactive_response = client.patch(f"/providers/{provider['id']}", json={"is_active": False})
        assert inactive_response.status_code == 200
        assignment_response = client.put(
            f"/agent-assignments/{DEMAND_VALIDATOR_AGENT_ID}",
            json={"provider_id": provider["id"]},
        )
        assert assignment_response.status_code == 200
        stage_id = create_stage_id(client, DEMAND_VALIDATOR_AGENT_ID)

        response = client.get(f"/stages/{stage_id}/provider-setup-guidance")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_status"] == "blocked"
    assert body["reason"] == "assigned_provider_inactive"
    assert body["can_run"] is False
    assert body["provider_id"] == provider["id"]
    assert body["provider_name"] == "inactive-shared"
    assert body["provider_source"] == "agent_default"
    assert body["setup_actions"] == [
        "Activate the assigned provider or choose another active provider.",
    ]


def test_provider_setup_guidance_rejects_other_users_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'provider-guidance-permission.db'}")

    with TestClient(app) as client:
        register_and_login(client, "GUIDE-OWNER", "guide-owner@example.com")
        stage_id = create_stage_id(client, DEMAND_VALIDATOR_AGENT_ID)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "GUIDE-OTHER", "guide-other@example.com")

        response = client.get(f"/stages/{stage_id}/provider-setup-guidance")

    assert response.status_code == 403
