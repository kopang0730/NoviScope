from fastapi.testclient import TestClient
from sqlmodel import Session, select

from noviscope.core.json_types import JsonObject
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


def create_shared_provider(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/providers",
        json={
            "api_key": "sk-matrix-secret",
            "base_url": "https://api.example.com/v1",
            "default_model": "example-chat",
            "kind": "openai_compatible",
            "name": "Shared Example",
            "scope": "shared",
        },
    )
    assert response.status_code == 201
    return response.json()


def matrix_agent(body: JsonObject, agent_id: str) -> JsonObject:
    agents = body["agents"]
    assert isinstance(agents, list)
    agent = next(
        agent
        for agent in agents
        if isinstance(agent, dict) and agent["agent_id"] == agent_id
    )
    assert isinstance(agent, dict)
    return agent


def test_agent_provider_matrix_requires_authentication(dev_admin_header_enabled: None) -> None:
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.get("/agent-provider-matrix")

    assert response.status_code == 401


def test_agent_provider_matrix_reports_provider_gaps_without_api_keys(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'agent-provider-matrix-empty.db'}")

    with TestClient(app) as client:
        register_and_login(client, "MATRIX-EMPTY", "matrix-empty@example.com")
        response = client.get("/agent-provider-matrix")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 9
    assert body["runnable_count"] == 1
    assert body["blocked_count"] == 8
    assert "sk-" not in str(body)

    demand = matrix_agent(body, "demand_validator")
    assert demand["provider_requirement"] == "model_provider"
    assert demand["stage_runner_available"] is True
    assert demand["can_run_with_current_config"] is False
    assert demand["unavailable_reason"] == "missing_provider"
    assert demand["assigned_provider"] is None
    assert demand["selected_provider"] is None
    assert demand["effective_model"] is None

    literature = matrix_agent(body, "literature_scout")
    assert literature["provider_requirement"] == "server_managed"
    assert literature["can_run_with_current_config"] is True
    assert literature["uses_server_managed_provider"] is True
    assert literature["selected_provider"]["id"] == "server_openalex"
    assert literature["effective_model"] == "openalex-works"

    code_runner = matrix_agent(body, "code_runner")
    assert code_runner["provider_requirement"] == "not_implemented"
    assert code_runner["can_run_with_current_config"] is False
    assert code_runner["unavailable_reason"] == "stage_runner_not_implemented"


def test_agent_provider_matrix_uses_admin_assignment_model_override(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'agent-provider-matrix-assigned.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        register_and_login(client, "MATRIX-ASSIGNED", "matrix-admin@example.com")
        promote_user_to_admin(database_url, "matrix-admin@example.com")
        provider = create_shared_provider(client)
        assignment_response = client.put(
            "/agent-assignments/demand_validator",
            json={"model_name": "example-chat-mini", "provider_id": provider["id"]},
        )
        response = client.get("/agent-provider-matrix")

    assert assignment_response.status_code == 200
    assert response.status_code == 200
    body = response.json()
    assert "sk-matrix-secret" not in str(body)

    demand = matrix_agent(body, "demand_validator")
    assert demand["can_run_with_current_config"] is True
    assert demand["unavailable_reason"] is None
    assert demand["selection_source"] == "agent_assignment"
    assert demand["assigned_provider"]["id"] == provider["id"]
    assert demand["selected_provider"]["id"] == provider["id"]
    assert demand["model_name"] == "example-chat-mini"
    assert demand["effective_model"] == "example-chat-mini"

    experiment = matrix_agent(body, "experiment_planner")
    assert experiment["can_run_with_current_config"] is True
    assert experiment["selection_source"] == "auto_available_provider"
    assert experiment["selected_provider"]["id"] == provider["id"]
    assert experiment["effective_model"] == "example-chat"


def test_agent_provider_matrix_blocks_inactive_assigned_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'agent-provider-matrix-inactive.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        register_and_login(client, "MATRIX-INACTIVE", "matrix-inactive@example.com")
        promote_user_to_admin(database_url, "matrix-inactive@example.com")
        provider = create_shared_provider(client)
        assignment_response = client.put(
            "/agent-assignments/demand_validator",
            json={"provider_id": provider["id"]},
        )
        inactive_response = client.patch(f"/providers/{provider['id']}", json={"is_active": False})
        response = client.get("/agent-provider-matrix")

    assert assignment_response.status_code == 200
    assert inactive_response.status_code == 200
    assert response.status_code == 200
    demand = matrix_agent(response.json(), "demand_validator")
    assert demand["can_run_with_current_config"] is False
    assert demand["unavailable_reason"] == "inactive_assigned_provider"
    assert demand["assigned_provider"]["is_active"] is False
    assert demand["selected_provider"] is None
