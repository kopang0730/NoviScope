from fastapi.testclient import TestClient

from noviscope.core.json_types import JsonObject
from noviscope.main import create_app

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


def register_and_login(client: TestClient) -> None:
    invite_response = client.post(
        "/admin/invites",
        headers=DEV_ADMIN_HEADERS,
        json={"code": "canvas-state-invite", "max_uses": 1},
    )
    assert invite_response.status_code == 201
    register_response = client.post(
        "/auth/register",
        json={
            "display_name": "Canvas Tester",
            "email": "canvas-state@example.com",
            "invite_code": "canvas-state-invite",
            "password": "password",
        },
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/auth/login",
        json={"email": "canvas-state@example.com", "password": "password"},
    )
    assert login_response.status_code == 200


def create_personal_provider(client: TestClient) -> JsonObject:
    response = client.post(
        "/providers",
        json={
            "api_key": "sk-test-canvas-state",
            "base_url": "https://api.example.com/v1",
            "default_model": "example-chat",
            "kind": "openai_compatible",
            "name": "Canvas Provider",
            "scope": "personal",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_quest(client: TestClient) -> JsonObject:
    response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision for badminton training.",
            "title": "Badminton training",
        },
    )
    assert response.status_code == 201
    return response.json()


def node_by_agent(body: JsonObject, agent_id: str) -> JsonObject:
    nodes = body["nodes"]
    assert isinstance(nodes, list)
    node = next(node for node in nodes if isinstance(node, dict) and node["agent_id"] == agent_id)
    assert isinstance(node, dict)
    return node


def test_workflow_canvas_state_requires_authentication(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'canvas-state-auth.db'}")

    with TestClient(app) as client:
        response = client.get("/quests/quest_missing/workflow-canvas-state")

    assert response.status_code == 401


def test_workflow_canvas_state_exposes_full_canvas_without_provider(
    dev_admin_header_enabled: None,
    tmp_path,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'canvas-state-empty.db'}")

    with TestClient(app) as client:
        register_and_login(client)
        quest = create_quest(client)
        response = client.get(f"/quests/{quest['id']}/workflow-canvas-state")

    assert response.status_code == 200
    body = response.json()
    assert body["quest"]["id"] == quest["id"]
    assert body["total_node_count"] == 9
    assert body["stage_node_count"] == 5
    assert body["planned_node_count"] == 4
    assert body["runnable_node_count"] == 0
    assert body["next_action_agent_id"] is None
    assert len(body["lanes"]) == 4
    assert len(body["edges"]) == 11
    assert "sk-" not in str(body)

    demand = node_by_agent(body, "demand_validator")
    assert demand["stage_id"] == quest["first_stage"]["id"]
    assert demand["implementation_status"] == "implemented_stage"
    assert demand["can_run"] is False
    assert demand["blocking_reason"] == "missing_provider"

    code_runner = node_by_agent(body, "code_runner")
    assert code_runner["stage_id"] is None
    assert code_runner["implementation_status"] == "planned_extension"
    assert code_runner["can_run"] is False
    assert code_runner["blocking_reason"] == "planned_agent"
    assert code_runner["status"] is None


def test_workflow_canvas_state_reports_next_action_and_provider(
    dev_admin_header_enabled: None,
    tmp_path,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'canvas-state-provider.db'}")

    with TestClient(app) as client:
        register_and_login(client)
        provider = create_personal_provider(client)
        quest = create_quest(client)
        response = client.get(f"/quests/{quest['id']}/workflow-canvas-state")

    assert response.status_code == 200
    body = response.json()
    assert body["runnable_node_count"] == 1
    assert body["next_action_agent_id"] == "demand_validator"
    assert body["next_action_stage_id"] == quest["first_stage"]["id"]
    assert "sk-test-canvas-state" not in str(body)

    demand = node_by_agent(body, "demand_validator")
    assert demand["can_run"] is True
    assert demand["provider_id"] == provider["id"]
    assert demand["provider_model"] == "example-chat"
    assert demand["provider_name"] == "Canvas Provider"

    literature = node_by_agent(body, "literature_scout")
    assert literature["can_run"] is False
    assert literature["blocking_reason"] == "demand_validation_incomplete"
