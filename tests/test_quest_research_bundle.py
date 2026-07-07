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


def create_quest_with_paper_stage(client: TestClient) -> tuple[str, str]:
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
    stages = stages_response.json()["stages"]
    paper_stage = next(
        stage for stage in stages if stage["agent_id"] == PAPER_MEETING_WRITER_AGENT_ID
    )
    return quest_id, paper_stage["id"]


def complete_paper_stage_with_artifacts(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "output_payload": {
                "chinese_research_brief_markdown": "# 中文研究 Brief\n\n已验证需求来自训练反馈。",
                "confidence": "medium",
                "english_research_brief_markdown": "# Research Brief\n\nVerified demand.",
                "experiment_results_not_available": [
                    "No baseline or ablation metrics are available yet."
                ],
                "human_review_required": [
                    "Confirm the dataset license before experiments."
                ],
                "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\nResults: TBD.",
                "meeting_outline_markdown": "# Meeting Outline\n\n1. Demand\n2. Evidence",
                "model_generated_hypotheses": [
                    "Temporal context may improve badminton action recognition."
                ],
                "raw_response": "raw provider payload must stay out of the bundle",
                "source_stage_ids": {
                    "demand_validation": "demand-stage-id",
                    "experiment_planner": "experiment-stage-id",
                    "idea_generator": "idea-stage-id",
                    "literature_scout": "literature-stage-id",
                },
                "verified_facts": ["The quest targets badminton training feedback."],
                "warnings": ["Review the application demand before claiming impact."],
            },
            "status": "complete",
            "summary": "Generated four traceable Markdown artifacts.",
        },
    )
    assert complete_response.status_code == 200


def test_research_brief_bundle_downloads_traceable_markdown(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'research-bundle.db'}")

    with TestClient(app) as client:
        register_and_login(client, "BUNDLE-OK", "bundle-ok@example.com")
        quest_id, paper_stage_id = create_quest_with_paper_stage(client)
        complete_paper_stage_with_artifacts(client, paper_stage_id)

        response = client.get(f"/quests/{quest_id}/research-brief/download")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert 'filename="noviscope-research-brief-bundle.md"' in response.headers[
        "content-disposition"
    ]
    markdown = response.text
    assert "# NoviScope Research Brief Bundle" in markdown
    assert "## Trust & Review Status" in markdown
    assert "Confidence: medium" in markdown
    assert "Human approved: No" in markdown
    assert "demand_validation: demand-stage-id" in markdown
    assert "## Human Review Required" in markdown
    assert "Confirm the dataset license before experiments." in markdown
    assert "## Experiment Results Status" in markdown
    assert "No baseline or ablation metrics are available yet." in markdown
    assert "## Chinese Research Brief" in markdown
    assert "## English Research Brief" in markdown
    assert "## Meeting Outline" in markdown
    assert "## IEEE Paper Skeleton" in markdown
    assert "raw provider payload" not in markdown


def test_research_brief_bundle_blocks_until_paper_writer_completes(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'research-bundle-blocked.db'}")

    with TestClient(app) as client:
        register_and_login(client, "BUNDLE-BLOCK", "bundle-block@example.com")
        quest_id, _ = create_quest_with_paper_stage(client)

        response = client.get(f"/quests/{quest_id}/research-brief/download")

    assert response.status_code == 409
    assert "Paper & Meeting Writer must complete" in response.json()["detail"]


def test_research_brief_bundle_rejects_other_users_quest(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'research-bundle-permission.db'}")

    with TestClient(app) as client:
        register_and_login(client, "BUNDLE-OWNER", "bundle-owner@example.com")
        quest_id, paper_stage_id = create_quest_with_paper_stage(client)
        complete_paper_stage_with_artifacts(client, paper_stage_id)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "BUNDLE-OTHER", "bundle-other@example.com")

        response = client.get(f"/quests/{quest_id}/research-brief/download")

    assert response.status_code == 403
