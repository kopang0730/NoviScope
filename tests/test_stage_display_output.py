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


def create_quest_with_demand_stage(client: TestClient) -> str:
    quest_response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision for badminton training feedback.",
            "title": "Badminton training feedback",
        },
    )
    assert quest_response.status_code == 201
    quest_id = quest_response.json()["id"]
    stages_response = client.get(f"/quests/{quest_id}/stages")
    assert stages_response.status_code == 200
    stages = stages_response.json()["stages"]
    demand_stage = next(stage for stage in stages if stage["agent_id"] == DEMAND_VALIDATOR_AGENT_ID)
    return demand_stage["id"]


def complete_demand_stage_with_raw_response(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "output_payload": {
                "confidence": "medium",
                "evidence_for_demand": [
                    "Court owners need repeatable badminton training feedback."
                ],
                "raw_response": "provider response should not be in the default UI",
                "risks": ["Demand source still needs external verification."],
                "summary": "Demand is plausible but requires human review.",
                "trace": {
                    "token": "provider-token-should-stay-hidden",
                    "raw_response": "nested provider details should also stay hidden",
                    "stage": "demand_validation",
                },
            },
            "status": "complete",
            "summary": "Demand is plausible but requires human review.",
        },
    )
    assert complete_response.status_code == 200


def test_stage_display_output_hides_raw_model_responses(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-display-output.db'}")

    with TestClient(app) as client:
        # Given a completed stage with raw model response fields.
        register_and_login(client, "DISPLAY-OUTPUT", "display-output@example.com")
        demand_stage_id = create_quest_with_demand_stage(client)
        complete_demand_stage_with_raw_response(client, demand_stage_id)

        # When the owner asks for default display output.
        response = client.get(f"/stages/{demand_stage_id}/display-output")

    # Then the display payload keeps structured evidence but hides raw responses.
    assert response.status_code == 200
    body = response.json()
    assert body["stage_id"] == demand_stage_id
    assert body["agent_id"] == DEMAND_VALIDATOR_AGENT_ID
    assert body["output_available"] is True
    assert body["raw_response_available"] is True
    assert body["confidence"] == "medium"
    assert body["summary"] == "Demand is plausible but requires human review."
    assert body["display_payload"]["evidence_for_demand"] == [
        "Court owners need repeatable badminton training feedback."
    ]
    assert "raw_response" not in body["display_payload"]
    assert "raw_response" not in body["display_payload"]["trace"]
    assert "token" not in body["display_payload"]["trace"]
    assert body["hidden_fields"] == [
        "output_payload.raw_response",
        "output_payload.trace.token",
        "output_payload.trace.raw_response",
    ]


def test_stage_display_output_marks_pending_stage_without_output(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-display-pending.db'}")

    with TestClient(app) as client:
        # Given a stage that has not produced model output.
        register_and_login(client, "DISPLAY-PENDING", "display-pending@example.com")
        demand_stage_id = create_quest_with_demand_stage(client)

        # When the owner asks for default display output.
        response = client.get(f"/stages/{demand_stage_id}/display-output")

    # Then the API gives the frontend an explicit empty state.
    assert response.status_code == 200
    body = response.json()
    assert body["output_available"] is False
    assert body["raw_response_available"] is False
    assert body["display_payload"] == {}
    assert body["hidden_fields"] == []
    assert body["confidence"] == "unknown"


def test_stage_display_output_rejects_other_users_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-display-permission.db'}")

    with TestClient(app) as client:
        # Given one user owns a stage with displayable output.
        register_and_login(client, "DISPLAY-OWNER", "display-owner@example.com")
        demand_stage_id = create_quest_with_demand_stage(client)
        complete_demand_stage_with_raw_response(client, demand_stage_id)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "DISPLAY-OTHER", "display-other@example.com")

        # When another user asks for default display output.
        response = client.get(f"/stages/{demand_stage_id}/display-output")

    # Then ownership rules prevent cross-user output access.
    assert response.status_code == 403
