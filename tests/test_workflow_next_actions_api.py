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


def create_personal_provider(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/providers",
        json={
            "api_key": "sk-test-next-actions",
            "base_url": "https://api.example.com/v1",
            "default_model": "example-chat",
            "kind": "openai_compatible",
            "name": "Example Provider",
            "scope": "personal",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_quest(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision to erase handwritten text.",
            "title": "Handwritten text erasure",
        },
    )
    assert response.status_code == 201
    quest_id = response.json()["id"]
    stages_response = client.get(f"/quests/{quest_id}/stages")
    assert stages_response.status_code == 200
    demand_stage = next(
        stage
        for stage in stages_response.json()["stages"]
        if stage["agent_id"] == DEMAND_VALIDATOR_AGENT_ID
    )
    return quest_id, demand_stage["id"]


def complete_unapproved_demand_stage(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    response = client.patch(
        f"/stages/{stage_id}",
        json={
            "human_approved": False,
            "output_payload": {
                "confidence": "medium",
                "demand_assessment": "plausible",
                "evidence_for_demand": ["worksheet reuse workflow"],
            },
            "review_notes": "Need stronger customer evidence before continuing.",
            "status": "complete",
            "summary": "Demand is plausible but needs review.",
        },
    )
    assert response.status_code == 200


def test_workflow_next_actions_prioritizes_provider_configuration(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'workflow-next-actions.db'}")
    with TestClient(app) as client:
        # Given: a new Quest without any runnable model provider.
        register_and_login(client, "NEXT-ACTIONS-PROVIDER", "next-actions-provider@example.com")
        quest_id, demand_stage_id = create_quest(client)

        # When: the workbench asks what the user should do next.
        response = client.get(f"/quests/{quest_id}/workflow-next-actions")

    # Then: the first action is provider configuration, not a fake run suggestion.
    assert response.status_code == 200
    body = response.json()
    assert body["quest_id"] == quest_id
    assert body["action_count"] == 1
    assert body["actions"][0] == {
        "action_type": "configure_provider",
        "agent_id": DEMAND_VALIDATOR_AGENT_ID,
        "blocking_reason": "missing_provider",
        "can_run": False,
        "detail": "Configure an active supported provider before running this stage.",
        "label": "Configure provider for Demand validation",
        "priority": 1,
        "stage_id": demand_stage_id,
        "stage_status": "pending",
        "stage_title": "Demand validation",
    }


def test_workflow_next_actions_prioritizes_human_review_gate(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'workflow-next-actions-review.db'}")
    with TestClient(app) as client:
        # Given: Demand validation is complete but explicitly not approved.
        register_and_login(client, "NEXT-ACTIONS-REVIEW", "next-actions-review@example.com")
        create_personal_provider(client)
        quest_id, demand_stage_id = create_quest(client)
        complete_unapproved_demand_stage(client, demand_stage_id)

        # When: the workbench asks what blocks the research workflow.
        response = client.get(f"/quests/{quest_id}/workflow-next-actions")

    # Then: the next action is human review before downstream stages run.
    assert response.status_code == 200
    body = response.json()
    assert body["action_count"] == 1
    assert body["actions"][0]["action_type"] == "review_stage"
    assert body["actions"][0]["agent_id"] == DEMAND_VALIDATOR_AGENT_ID
    assert body["actions"][0]["stage_id"] == demand_stage_id
    assert body["actions"][0]["label"] == "Review Demand validation"
    assert body["actions"][0]["detail"] == "Need stronger customer evidence before continuing."
    assert body["actions"][0]["can_run"] is False
