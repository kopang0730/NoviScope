from fastapi.testclient import TestClient
from pydantic import JsonValue

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


def create_quest_with_stage_ids(client: TestClient) -> tuple[str, dict[str, str]]:
    quest_response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision for badminton action recognition.",
            "title": "Badminton action recognition",
        },
    )
    assert quest_response.status_code == 201
    quest_id = quest_response.json()["id"]
    stages_response = client.get(f"/quests/{quest_id}/stages")
    assert stages_response.status_code == 200
    stage_ids = {
        stage["agent_id"]: stage["id"] for stage in stages_response.json()["stages"]
    }
    return quest_id, stage_ids


def patch_stage(
    client: TestClient,
    stage_id: str,
    payload: dict[str, JsonValue],
) -> None:
    response = client.patch(f"/stages/{stage_id}", json=payload)
    assert response.status_code == 200


def test_stage_transition_audit_records_status_changes_only(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-transitions.db'}")
    with TestClient(app) as client:
        register_and_login(client, "STAGE-TRANSITIONS", "stage-transitions@example.com")
        quest_id, stage_ids = create_quest_with_stage_ids(client)
        stage_id = stage_ids[DEMAND_VALIDATOR_AGENT_ID]
        patch_stage(
            client,
            stage_id,
            {
                "input_payload": {
                    "provider_id": "provider_123",
                    "provider_model": "gpt-4.1",
                    "provider_name": "GPT Lab",
                },
                "status": "running",
            },
        )
        patch_stage(
            client,
            stage_id,
            {
                "summary": "Updated while already running.",
                "status": "running",
            },
        )
        patch_stage(
            client,
            stage_id,
            {
                "evidence_payload": {
                    "blocking_detail": "Provider timed out.",
                    "blocking_reason": "runner_error",
                    "provider_model": "gpt-4.1",
                },
                "status": "blocked",
                "summary": "Runner failed.",
            },
        )

        response = client.get(f"/quests/{quest_id}/stage-transitions")

    assert response.status_code == 200
    body = response.json()
    assert body["transition_count"] == 2
    assert body["quest_id"] == quest_id
    running_event, blocked_event = body["events"]
    assert running_event["from_status"] == "pending"
    assert running_event["to_status"] == "running"
    assert running_event["provider_model"] == "gpt-4.1"
    assert running_event["blocking_reason"] == ""
    assert blocked_event["from_status"] == "running"
    assert blocked_event["to_status"] == "blocked"
    assert blocked_event["blocking_reason"] == "runner_error"
    assert blocked_event["blocking_detail"] == "Provider timed out."


def test_stage_transition_audit_rejects_other_user_quest(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-transitions-auth.db'}")
    with TestClient(app) as client:
        register_and_login(client, "STAGE-TRANSITIONS-ONE", "stage-transitions-one@example.com")
        quest_id, _ = create_quest_with_stage_ids(client)
        client.post("/auth/logout")
        register_and_login(client, "STAGE-TRANSITIONS-TWO", "stage-transitions-two@example.com")

        response = client.get(f"/quests/{quest_id}/stage-transitions")

    assert response.status_code == 403
