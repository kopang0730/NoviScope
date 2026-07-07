from fastapi.testclient import TestClient

from noviscope.core.stage_policy import DEMAND_VALIDATOR_AGENT_ID
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


def create_quest(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision for badminton action recognition.",
            "title": "Badminton action recognition",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_personal_provider(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/providers",
        json={
            "api_key": "sk-test-autopilot",
            "base_url": "https://api.example.com/v1",
            "default_model": "example-chat",
            "kind": "openai_compatible",
            "name": "Example Provider",
            "scope": "personal",
        },
    )
    assert response.status_code == 201
    return response.json()


def complete_demand_without_human_approval(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "output_payload": {
                "confidence": "medium",
                "demand_assessment": "plausible",
            },
            "status": "complete",
            "summary": "Demand validation output is ready for human review.",
        },
    )
    assert complete_response.status_code == 200


def test_workflow_autopilot_plan_reports_next_runnable_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'autopilot-ready.db'}")

    with TestClient(app) as client:
        register_and_login(client, "AUTOPILOT-READY", "autopilot-ready@example.com")
        quest = create_quest(client)
        provider = create_personal_provider(client)

        response = client.get(f"/quests/{quest['id']}/autopilot-plan")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_to_run"
    assert body["next_stage_id"] == quest["first_stage"]["id"]
    assert body["next_stage_title"] == "Demand validation"
    assert body["summary"] == "Autopilot can run Demand validation next."
    first_step = body["steps"][0]
    assert first_step["agent_id"] == DEMAND_VALIDATOR_AGENT_ID
    assert first_step["action"] == "run_next"
    assert first_step["provider_id"] == provider["id"]
    assert "sk-test-autopilot" not in str(body)


def test_workflow_autopilot_plan_stops_at_human_review_gate(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'autopilot-review.db'}")

    with TestClient(app) as client:
        register_and_login(client, "AUTOPILOT-REVIEW", "autopilot-review@example.com")
        quest = create_quest(client)
        create_personal_provider(client)
        complete_demand_without_human_approval(client, quest["first_stage"]["id"])

        response = client.get(f"/quests/{quest['id']}/autopilot-plan")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "waiting_for_human_review"
    assert body["next_stage_id"] is None
    assert body["stop_stage_id"] == quest["first_stage"]["id"]
    assert body["summary"] == "Autopilot is waiting for human review on Demand validation."
    first_step = body["steps"][0]
    assert first_step["action"] == "await_human_review"
    assert first_step["requires_human_review"] is True
