from fastapi.testclient import TestClient

from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
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


def create_reviewable_quest(client: TestClient) -> str:
    quest_response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision for badminton trajectory recognition.",
            "title": "Badminton trajectory recognition",
        },
    )
    assert quest_response.status_code == 201
    quest_id = quest_response.json()["id"]
    stages_response = client.get(f"/quests/{quest_id}/stages")
    assert stages_response.status_code == 200
    stages = stages_response.json()["stages"]
    demand_stage = next(stage for stage in stages if stage["agent_id"] == DEMAND_VALIDATOR_AGENT_ID)
    paper_stage = next(
        stage for stage in stages if stage["agent_id"] == PAPER_MEETING_WRITER_AGENT_ID
    )
    demand_running_response = client.patch(
        f"/stages/{demand_stage['id']}",
        json={"status": "running"},
    )
    assert demand_running_response.status_code == 200
    demand_response = client.patch(
        f"/stages/{demand_stage['id']}",
        json={
            "evidence_payload": {
                "human_demand_sources": ["Coach feedback interview"],
                "human_demand_verdict": "verified",
            },
            "human_approved": True,
            "output_payload": {
                "confidence": "medium",
                "demand_assessment": "plausible",
                "human_review_required": ["Confirm video consent scope."],
            },
            "review_notes": "Demand is worth scouting.",
            "status": "complete",
            "summary": "Demand has a real training scenario.",
        },
    )
    assert demand_response.status_code == 200
    paper_running_response = client.patch(
        f"/stages/{paper_stage['id']}",
        json={"status": "running"},
    )
    assert paper_running_response.status_code == 200
    paper_response = client.patch(
        f"/stages/{paper_stage['id']}",
        json={
            "output_payload": {
                "chinese_research_brief_markdown": "# 中文研究 Brief\n\n## 已验证事实",
                "confidence": "medium",
                "english_research_brief_markdown": "# Research Brief\n\n## Verified Facts",
                "experiment_results_not_available": ["No training run has been executed."],
                "human_review_required": ["Review claims before group meeting."],
                "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\n## Results\nTBD.",
                "meeting_outline_markdown": "# Group Meeting Outline\n\n1. Motivation",
                "model_generated_hypotheses": ["Temporal consistency may reduce jitter."],
                "verified_facts": ["A coach feedback scenario exists."],
            },
            "status": "complete",
            "summary": "Generated review-only writing artifacts.",
        },
    )
    assert paper_response.status_code == 200
    return quest_id


def test_download_quest_review_packet_returns_markdown_attachment(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    # Given: an owner has a quest with saved review evidence and draft writing.
    app = create_app(database_url=f"sqlite:///{tmp_path / 'quest-review-packet.db'}")
    with TestClient(app) as client:
        register_and_login(client, "QUEST-REVIEW-PACKET", "packet-owner@example.com")
        quest_id = create_reviewable_quest(client)

        # When: the owner downloads the review packet.
        response = client.get(f"/quests/{quest_id}/review-packet/download")

    # Then: the packet is a traceable Markdown attachment, not an experiment claim.
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"] == (
        'attachment; filename="badminton-trajectory-recognition-review-packet.md"'
    )
    assert "# NoviScope Quest Review Packet: Badminton trajectory recognition" in response.text
    assert "Review-only export" in response.text
    assert "Demand has a real training scenario." in response.text
    assert "No training run has been executed." in response.text
    assert "## Output Payload" in response.text
    assert "## Evidence Payload" in response.text
    assert "api_key" not in response.text.lower()


def test_download_quest_review_packet_rejects_other_member(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    # Given: one member owns a quest and a second member is logged in.
    app = create_app(database_url=f"sqlite:///{tmp_path / 'quest-review-packet-access.db'}")
    with TestClient(app) as client:
        register_and_login(client, "QUEST-PACKET-OWNER", "packet-owner@example.com")
        quest_id = create_reviewable_quest(client)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "QUEST-PACKET-OTHER", "packet-other@example.com")

        # When: the second member tries to download the owner's packet.
        response = client.get(f"/quests/{quest_id}/review-packet/download")

    # Then: quest ownership is enforced for review packet downloads.
    assert response.status_code == 403
