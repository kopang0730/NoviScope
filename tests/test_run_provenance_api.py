from fastapi.testclient import TestClient
from pydantic import JsonValue

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.core.json_types import JsonObject
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


def patch_stage(client: TestClient, stage_id: str, payload: JsonObject) -> None:
    response = client.patch(f"/stages/{stage_id}", json=payload)
    assert response.status_code == 200


def complete_stage(
    client: TestClient,
    stage_id: str,
    payload: dict[str, JsonValue],
) -> None:
    patch_stage(client, stage_id, {"status": "running"})
    patch_stage(client, stage_id, {**payload, "status": "complete"})


def entry_by_agent(body: JsonObject, agent_id: str) -> JsonObject:
    entries = body["entries"]
    assert isinstance(entries, list)
    for entry in entries:
        assert isinstance(entry, dict)
        if entry["agent_id"] == agent_id:
            return entry
    raise AssertionError(f"Missing provenance entry for {agent_id}")


def test_run_provenance_reports_draft_quest_without_fake_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'run-provenance-draft.db'}")
    with TestClient(app) as client:
        register_and_login(client, "RUN-PROV-DRAFT", "run-prov-draft@example.com")
        quest_id, _ = create_quest_with_stage_ids(client)

        response = client.get(f"/quests/{quest_id}/run-provenance")

    assert response.status_code == 200
    body = response.json()
    assert body["attempted_stage_count"] == 0
    assert body["total_stage_count"] == 5
    demand_entry = entry_by_agent(body, DEMAND_VALIDATOR_AGENT_ID)
    assert demand_entry["run_state"] == "not_started"
    assert demand_entry["provider_model"] == ""
    assert demand_entry["has_raw_response"] is False
    assert demand_entry["confidence"] == "unknown"


def test_run_provenance_summarizes_run_state_without_leaking_raw_response(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'run-provenance-state.db'}")
    with TestClient(app) as client:
        register_and_login(client, "RUN-PROV-STATE", "run-prov-state@example.com")
        quest_id, stage_ids = create_quest_with_stage_ids(client)
        complete_stage(
            client,
            stage_ids[DEMAND_VALIDATOR_AGENT_ID],
            {
                "evidence_payload": {
                    "can_run": True,
                    "provider_id": "provider_123",
                    "provider_kind": "openai_compatible",
                    "provider_model": "gpt-4.1",
                    "provider_name": "GPT Lab",
                    "requires_human_review": True,
                },
                "output_payload": {
                    "confidence": "medium",
                    "raw_response": "secret raw response that must not be returned",
                    "summary": "Demand appears plausible.",
                },
                "summary": "Demand appears plausible.",
            },
        )
        patch_stage(client, stage_ids[LITERATURE_SCOUT_AGENT_ID], {"status": "running"})
        patch_stage(
            client,
            stage_ids[LITERATURE_SCOUT_AGENT_ID],
            {
                "evidence_payload": {
                    "blocking_detail": "Complete Demand validation before running.",
                    "blocking_reason": "demand_validation_incomplete",
                    "can_run": False,
                },
                "status": "blocked",
                "summary": "Literature Scout is blocked.",
            },
        )

        response = client.get(f"/quests/{quest_id}/run-provenance")

    assert response.status_code == 200
    body = response.json()
    assert body["attempted_stage_count"] == 2
    assert body["blocked_stage_count"] == 1
    assert body["human_review_required_count"] == 1
    assert body["raw_response_count"] == 1
    assert "secret raw response" not in response.text
    demand_entry = entry_by_agent(body, DEMAND_VALIDATOR_AGENT_ID)
    assert demand_entry["run_state"] == "complete"
    assert demand_entry["provider_model"] == "gpt-4.1"
    assert demand_entry["provider_name"] == "GPT Lab"
    assert demand_entry["has_raw_response"] is True
    literature_entry = entry_by_agent(body, LITERATURE_SCOUT_AGENT_ID)
    assert literature_entry["run_state"] == "blocked"
    assert literature_entry["blocking_reason"] == "demand_validation_incomplete"
    assert literature_entry["can_run_recorded"] is False


def test_run_provenance_rejects_other_user_quest(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'run-provenance-auth.db'}")
    with TestClient(app) as client:
        register_and_login(client, "RUN-PROV-ONE", "run-prov-one@example.com")
        quest_id, _ = create_quest_with_stage_ids(client)
        client.post("/auth/logout")
        register_and_login(client, "RUN-PROV-TWO", "run-prov-two@example.com")

        response = client.get(f"/quests/{quest_id}/run-provenance")

    assert response.status_code == 403
