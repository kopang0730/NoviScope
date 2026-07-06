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


def complete_demand_stage(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "evidence_payload": {"requires_human_review": True},
            "output_payload": {
                "confidence": "medium",
                "evidence_for_demand": [
                    "Court owners need repeatable badminton training feedback."
                ],
                "missing_evidence": ["Need an external customer proof point."],
                "risks": ["The demand is still self-reported."],
                "suggested_human_checklist": [
                    "Call one badminton training customer before approving."
                ],
                "summary": "Demand is plausible but still needs a human source check.",
            },
            "status": "complete",
            "summary": "Demand is plausible but still needs a human source check.",
        },
    )
    assert complete_response.status_code == 200


def test_stage_review_guidance_marks_completed_stage_ready_for_review(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'review-guidance-ready.db'}")

    with TestClient(app) as client:
        # Given a completed stage with structured review evidence.
        register_and_login(client, "GUIDANCE-READY", "guidance-ready@example.com")
        demand_stage_id = create_quest_with_demand_stage(client)
        complete_demand_stage(client, demand_stage_id)

        # When the owner asks for review guidance.
        response = client.get(f"/stages/{demand_stage_id}/review-guidance")

    # Then the API returns an actionable human-review contract.
    assert response.status_code == 200
    body = response.json()
    assert body["stage_id"] == demand_stage_id
    assert body["agent_id"] == DEMAND_VALIDATOR_AGENT_ID
    assert body["status"] == "complete"
    assert body["approval_state"] == "ready_for_review"
    assert body["review_required"] is True
    assert body["can_approve"] is True
    assert body["blocking_reason"] == ""
    assert body["confidence"] == "medium"
    assert body["checklist"] == [
        "Call one badminton training customer before approving.",
        "Need an external customer proof point.",
        "The demand is still self-reported.",
    ]
    assert body["evidence_summary"] == ["Court owners need repeatable badminton training feedback."]


def test_stage_review_guidance_blocks_approval_before_stage_completion(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'review-guidance-pending.db'}")

    with TestClient(app) as client:
        # Given a stage that has not produced output yet.
        register_and_login(client, "GUIDANCE-PENDING", "guidance-pending@example.com")
        demand_stage_id = create_quest_with_demand_stage(client)

        # When the owner asks for review guidance.
        response = client.get(f"/stages/{demand_stage_id}/review-guidance")

    # Then the API explains why human approval is not actionable yet.
    assert response.status_code == 200
    body = response.json()
    assert body["approval_state"] == "pending_stage_completion"
    assert body["review_required"] is False
    assert body["can_approve"] is False
    assert body["blocking_reason"] == "Stage must complete before human review approval."
    assert body["checklist"] == ["Run or complete this stage before human review."]
    assert body["evidence_summary"] == []


def test_stage_review_guidance_marks_reviewed_stage_as_not_actionable(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'review-guidance-reviewed.db'}")

    with TestClient(app) as client:
        # Given a completed stage that a human already approved.
        register_and_login(client, "GUIDANCE-APPROVED", "guidance-approved@example.com")
        demand_stage_id = create_quest_with_demand_stage(client)
        complete_demand_stage(client, demand_stage_id)
        approve_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={
                "human_approved": True,
                "review_notes": "Human checked the customer source.",
            },
        )
        assert approve_response.status_code == 200

        # When the owner asks for review guidance.
        response = client.get(f"/stages/{demand_stage_id}/review-guidance")

    # Then the review card reports the final approval state without another approval CTA.
    assert response.status_code == 200
    body = response.json()
    assert body["approval_state"] == "approved"
    assert body["review_required"] is False
    assert body["can_approve"] is False
    assert body["review_notes"] == "Human checked the customer source."


def test_stage_review_guidance_rejects_other_users_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'review-guidance-permission.db'}")

    with TestClient(app) as client:
        # Given one user owns a stage.
        register_and_login(client, "GUIDANCE-OWNER", "guidance-owner@example.com")
        demand_stage_id = create_quest_with_demand_stage(client)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "GUIDANCE-OTHER", "guidance-other@example.com")

        # When another user asks for review guidance on that stage.
        response = client.get(f"/stages/{demand_stage_id}/review-guidance")

    # Then ownership rules prevent cross-user review metadata access.
    assert response.status_code == 403
