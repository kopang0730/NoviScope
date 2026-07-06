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


def stage_by_agent(client: TestClient, quest_id: str, agent_id: str) -> dict[str, str]:
    response = client.get(f"/quests/{quest_id}/stages")
    assert response.status_code == 200
    stages = response.json()["stages"]
    return next(stage for stage in stages if stage["agent_id"] == agent_id)


def create_personal_provider(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/providers",
        json={
            "api_key": "sk-test-readiness",
            "base_url": "https://api.example.com/v1",
            "default_model": "example-chat",
            "kind": "openai_compatible",
            "name": "Example Provider",
            "scope": "personal",
        },
    )
    assert response.status_code == 201
    return response.json()


def complete_demand_with_human_evidence(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    response = client.patch(
        f"/stages/{stage_id}",
        json={
            "evidence_payload": {
                "human_demand_sources": ["Coach interview note."],
                "human_demand_verdict": "verified",
            },
            "human_approved": True,
            "output_payload": {"confidence": "medium"},
            "status": "complete",
            "summary": "Demand was reviewed by a human.",
        },
    )
    assert response.status_code == 200


def test_stage_readiness_reports_missing_provider_without_mutating_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'readiness-missing-provider.db'}")

    with TestClient(app) as client:
        register_and_login(client, "READINESS-MISSING", "readiness-missing@example.com")
        quest = create_quest(client)
        stage_id = quest["first_stage"]["id"]

        response = client.get(f"/stages/{stage_id}/readiness")
        refreshed_stage = stage_by_agent(client, quest["id"], DEMAND_VALIDATOR_AGENT_ID)

    assert response.status_code == 200
    body = response.json()
    assert body["can_run"] is False
    assert body["blocking_reason"] == "missing_provider"
    assert body["blocking_detail"] == (
        "Configure an active supported provider before running this stage."
    )
    assert body["provider_id"] is None
    assert refreshed_stage["status"] == "pending"
    assert refreshed_stage["evidence_payload"] == {}


def test_stage_readiness_reports_model_provider_without_exposing_api_key(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'readiness-provider.db'}")

    with TestClient(app) as client:
        register_and_login(client, "READINESS-PROVIDER", "readiness-provider@example.com")
        quest = create_quest(client)
        provider = create_personal_provider(client)

        response = client.get(f"/stages/{quest['first_stage']['id']}/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["can_run"] is True
    assert body["provider_id"] == provider["id"]
    assert body["provider_kind"] == "openai_compatible"
    assert body["provider_model"] == "example-chat"
    assert body["provider_name"] == "Example Provider"
    assert "sk-test-readiness" not in str(body)


def test_stage_readiness_blocks_completed_stage_when_provider_exists(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'readiness-complete.db'}")

    with TestClient(app) as client:
        register_and_login(client, "READINESS-COMPLETE", "readiness-complete@example.com")
        quest = create_quest(client)
        create_personal_provider(client)
        complete_demand_with_human_evidence(client, quest["first_stage"]["id"])

        response = client.get(f"/stages/{quest['first_stage']['id']}/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["can_run"] is False
    assert body["blocking_reason"] == "stage_already_complete"
    assert body["blocking_detail"] == "Completed stages are locked until versioned reruns exist."
    assert body["provider_id"] is None


def test_stage_readiness_reports_server_managed_literature_provider(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'readiness-literature.db'}")

    with TestClient(app) as client:
        register_and_login(client, "READINESS-LITERATURE", "readiness-literature@example.com")
        quest = create_quest(client)
        complete_demand_with_human_evidence(client, quest["first_stage"]["id"])
        literature_stage = stage_by_agent(client, quest["id"], "literature_scout")

        response = client.get(f"/stages/{literature_stage['id']}/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["can_run"] is True
    assert body["provider_id"] == "server_openalex"
    assert body["provider_kind"] == "custom"
    assert body["provider_model"] == "openalex-works"
    assert body["provider_name"] == "OpenAlex"
    assert body["uses_server_managed_provider"] is True
