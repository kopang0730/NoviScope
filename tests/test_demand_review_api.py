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
            "initial_direction": "Erase handwritten answers from scanned worksheets.",
            "title": "Handwritten text erasure",
        },
    )
    assert quest_response.status_code == 201
    quest_id = quest_response.json()["id"]
    stages_response = client.get(f"/quests/{quest_id}/stages")
    assert stages_response.status_code == 200
    stages = stages_response.json()["stages"]
    demand_stage = next(stage for stage in stages if stage["agent_id"] == DEMAND_VALIDATOR_AGENT_ID)
    return demand_stage["id"]


def complete_demand_stage(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "evidence_payload": {
                "can_run": True,
                "requires_human_review": True,
                "source_policy": "model_only_no_external_source_verification",
            },
            "output_payload": {
                "confidence": "medium",
                "demand_assessment": "plausible",
                "go_or_no_go_recommendation": "go_with_human_review",
                "summary": "Worksheet restoration appears plausible.",
            },
            "status": "complete",
        },
    )
    assert complete_response.status_code == 200


def test_review_demand_with_evidence_approves_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'demand-review.db'}")
    with TestClient(app) as client:
        register_and_login(client, "DEMAND-REVIEW", "demand-review@example.com")
        stage_id = create_quest_with_demand_stage(client)
        complete_demand_stage(client, stage_id)

        response = client.post(
            f"/stages/{stage_id}/demand-review",
            json={
                "review_notes": "A worksheet vendor has this production restoration need.",
                "sources": [
                    "Internal interview with worksheet digitization team",
                    "Sample scanned worksheet batch from partner",
                ],
                "verdict": "verified",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_id"] == DEMAND_VALIDATOR_AGENT_ID
    assert body["status"] == "complete"
    assert body["human_approved"] is True
    assert body["review_notes"] == "A worksheet vendor has this production restoration need."
    assert body["evidence_payload"]["human_demand_verdict"] == "verified"
    assert body["evidence_payload"]["human_demand_sources"] == [
        "Internal interview with worksheet digitization team",
        "Sample scanned worksheet batch from partner",
    ]
    assert body["evidence_payload"]["human_demand_reviewed"] is True
    assert body["evidence_payload"]["human_go_or_no_go"] == "go"
    assert body["summary"] == "Human review approved demand validation as verified."


def test_review_demand_requires_source_when_approving(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'demand-review-source.db'}")
    with TestClient(app) as client:
        register_and_login(client, "DEMAND-SOURCE", "demand-source@example.com")
        stage_id = create_quest_with_demand_stage(client)
        complete_demand_stage(client, stage_id)

        response = client.post(
            f"/stages/{stage_id}/demand-review",
            json={"sources": [], "verdict": "plausible"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "At least one demand evidence source is required to approve demand."
    )


def test_review_demand_rejected_marks_stage_not_approved(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'demand-review-reject.db'}")
    with TestClient(app) as client:
        register_and_login(client, "DEMAND-REJECT", "demand-reject@example.com")
        stage_id = create_quest_with_demand_stage(client)
        complete_demand_stage(client, stage_id)

        response = client.post(
            f"/stages/{stage_id}/demand-review",
            json={
                "review_notes": "No concrete customer or dataset evidence yet.",
                "sources": [],
                "verdict": "rejected",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["human_approved"] is False
    assert body["evidence_payload"]["human_demand_verdict"] == "rejected"
    assert body["evidence_payload"]["human_go_or_no_go"] == "no_go"
    assert body["summary"] == "Human review rejected demand validation."
