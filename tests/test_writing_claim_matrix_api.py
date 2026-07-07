from fastapi.testclient import TestClient

from noviscope.core.stage_policy import PAPER_MEETING_WRITER_AGENT_ID
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


def create_paper_stage(client: TestClient) -> str:
    quest_response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision for badminton action recognition.",
            "title": "Badminton action recognition",
        },
    )
    assert quest_response.status_code == 201
    stages_response = client.get(f"/quests/{quest_response.json()['id']}/stages")
    assert stages_response.status_code == 200
    return next(
        stage["id"]
        for stage in stages_response.json()["stages"]
        if stage["agent_id"] == PAPER_MEETING_WRITER_AGENT_ID
    )


def complete_paper_stage(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "evidence_payload": {
                "artifact_count": 4,
                "no_experiment_results": True,
                "requires_human_review": True,
                "source_stage_ids": {
                    "demand_validation": "stage_demand",
                    "experiment_planner": "stage_experiment",
                    "idea_generator": "stage_idea",
                    "literature_scout": "stage_literature",
                },
            },
            "output_payload": {
                "chinese_research_brief_markdown": "# 中文研究简报\n",
                "confidence": "medium",
                "english_research_brief_markdown": "# English Research Brief\n",
                "experiment_results_not_available": [
                    (
                        "No experiment results are available yet; result sections must "
                        "stay as placeholders."
                    )
                ],
                "human_review_required": [
                    "Verify all cited papers before using this draft in a submission."
                ],
                "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\n## Results\nTBD.\n",
                "meeting_outline_markdown": "# Meeting Outline\n",
                "model_generated_hypotheses": [
                    "Temporal consistency may improve badminton action recognition."
                ],
                "source_stage_ids": {
                    "demand_validation": "stage_demand",
                    "experiment_planner": "stage_experiment",
                    "idea_generator": "stage_idea",
                    "literature_scout": "stage_literature",
                },
                "summary": "Generated review-only paper and meeting drafts.",
                "verified_facts": [
                    "The workflow has a selected idea and an experiment plan."
                ],
                "warnings": [
                    (
                        "Human review is required before any draft can be used as a paper "
                        "or meeting claim."
                    )
                ],
            },
            "status": "complete",
        },
    )
    assert complete_response.status_code == 200


def test_writing_claim_matrix_groups_claims_and_artifact_statuses(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'writing-claim-matrix.db'}")
    with TestClient(app) as client:
        register_and_login(client, "WRITE-MATRIX", "write-matrix@example.com")
        stage_id = create_paper_stage(client)
        complete_paper_stage(client, stage_id)

        response = client.get(f"/stages/{stage_id}/writing-claim-matrix")

    assert response.status_code == 200
    body = response.json()
    assert body["stage_id"] == stage_id
    assert body["unavailable_reason"] == ""
    assert body["no_experiment_results"] is True
    assert body["requires_human_review"] is True
    groups = {group["group_id"]: group for group in body["claim_groups"]}
    assert groups["verified_facts"]["items"] == [
        "The workflow has a selected idea and an experiment plan."
    ]
    assert groups["model_generated_hypotheses"]["items"] == [
        "Temporal consistency may improve badminton action recognition."
    ]
    assert groups["experiment_results_not_available"]["items"] == [
        "No experiment results are available yet; result sections must stay as placeholders."
    ]
    assert groups["human_review_required"]["items"] == [
        "Verify all cited papers before using this draft in a submission."
    ]
    assert all(artifact["available"] for artifact in body["artifacts"])
    assert body["source_stage_ids"] == {
        "demand_validation": "stage_demand",
        "experiment_planner": "stage_experiment",
        "idea_generator": "stage_idea",
        "literature_scout": "stage_literature",
    }


def test_writing_claim_matrix_reports_unavailable_pending_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'writing-claim-pending.db'}")
    with TestClient(app) as client:
        register_and_login(client, "WRITE-PENDING", "write-pending@example.com")
        stage_id = create_paper_stage(client)

        response = client.get(f"/stages/{stage_id}/writing-claim-matrix")

    assert response.status_code == 200
    body = response.json()
    assert body["claim_groups"] == []
    assert body["artifacts"] == []
    assert body["no_experiment_results"] is True
    assert body["requires_human_review"] is True
    assert body["unavailable_reason"] == (
        "Paper & Meeting Writer must complete before writing claim matrix rows are available."
    )
