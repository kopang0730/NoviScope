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


def create_quest_with_paper_stage(client: TestClient) -> str:
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
    return paper_stage["id"]


def complete_paper_stage_with_artifacts(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "output_payload": {
                "chinese_research_brief_markdown": (
                    "# 中文研究 Brief\n\n## 已验证事实\n- 有真实场景。"
                ),
                "confidence": "medium",
                "english_research_brief_markdown": (
                    "# Research Brief\n\n## Verified Facts\n- Real scenario."
                ),
                "experiment_results_not_available": [
                    "No experiment results are available yet."
                ],
                "human_review_required": ["Confirm data access."],
                "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\n## Results\nTBD.",
                "meeting_outline_markdown": "# Group Meeting Outline\n\n1. Motivation",
                "model_generated_hypotheses": [
                    "Temporal consistency may improve action labels."
                ],
                "source_stage_ids": {
                    "demand_validation": "stage-demand",
                    "experiment_planner": "stage-experiment",
                    "idea_generator": "stage-idea",
                    "literature_scout": "stage-literature",
                },
                "summary": "Generated traceable draft artifacts.",
                "verified_facts": ["The demand scenario is coach feedback."],
                "warnings": ["Drafts are not submission-ready until human review."],
            },
            "status": "complete",
        },
    )
    assert complete_response.status_code == 200


def test_download_paper_markdown_artifact_returns_attachment(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'artifact-download.db'}")

    with TestClient(app) as client:
        register_and_login(client, "ARTIFACT-DOWNLOAD", "artifact@example.com")
        paper_stage_id = create_quest_with_paper_stage(client)
        complete_paper_stage_with_artifacts(client, paper_stage_id)

        response = client.get(
            f"/stages/{paper_stage_id}/artifacts/chinese_research_brief_markdown/download"
        )

    assert response.status_code == 200
    assert response.text.startswith("# 中文研究 Brief")
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"] == (
        'attachment; filename="noviscope-chinese-research-brief.md"'
    )


def test_list_paper_markdown_artifacts_returns_download_manifest(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'artifact-manifest.db'}")

    with TestClient(app) as client:
        register_and_login(client, "ARTIFACT-MANIFEST", "manifest@example.com")
        paper_stage_id = create_quest_with_paper_stage(client)
        complete_paper_stage_with_artifacts(client, paper_stage_id)

        response = client.get(f"/stages/{paper_stage_id}/artifacts")

    assert response.status_code == 200
    body = response.json()
    assert body["stage_id"] == paper_stage_id
    assert [artifact["key"] for artifact in body["artifacts"]] == [
        "chinese_research_brief_markdown",
        "english_research_brief_markdown",
        "meeting_outline_markdown",
        "ieee_paper_skeleton_markdown",
    ]
    first_artifact = body["artifacts"][0]
    assert first_artifact == {
        "available": True,
        "download_url": (
            f"/stages/{paper_stage_id}/artifacts/"
            "chinese_research_brief_markdown/download"
        ),
        "filename": "noviscope-chinese-research-brief.md",
        "key": "chinese_research_brief_markdown",
        "media_type": "text/markdown",
        "missing_reason": "",
        "title": "Chinese research brief",
    }


def test_list_paper_markdown_artifacts_includes_trust_summary(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'artifact-trust.db'}")

    with TestClient(app) as client:
        # Given
        register_and_login(client, "ARTIFACT-TRUST", "trust@example.com")
        paper_stage_id = create_quest_with_paper_stage(client)
        complete_paper_stage_with_artifacts(client, paper_stage_id)

        # When
        response = client.get(f"/stages/{paper_stage_id}/artifacts")

    # Then
    assert response.status_code == 200
    trust_summary = response.json()["trust_summary"]
    assert trust_summary == {
        "experiment_results_available": False,
        "experiment_results_not_available": ["No experiment results are available yet."],
        "human_review_required": ["Confirm data access."],
        "requires_human_review": True,
        "source_stage_ids": {
            "demand_validation": "stage-demand",
            "experiment_planner": "stage-experiment",
            "idea_generator": "stage-idea",
            "literature_scout": "stage-literature",
        },
        "warnings": ["Drafts are not submission-ready until human review."],
    }


def test_list_paper_markdown_artifacts_marks_incomplete_stage_unavailable(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'artifact-manifest-block.db'}")

    with TestClient(app) as client:
        register_and_login(client, "ARTIFACT-MANIFEST-BLOCK", "manifest-block@example.com")
        paper_stage_id = create_quest_with_paper_stage(client)

        response = client.get(f"/stages/{paper_stage_id}/artifacts")

    assert response.status_code == 200
    body = response.json()
    assert {artifact["available"] for artifact in body["artifacts"]} == {False}
    assert {artifact["missing_reason"] for artifact in body["artifacts"]} == {
        "Paper & Meeting Writer must complete before Markdown artifacts can be downloaded.",
    }


def test_download_paper_markdown_artifact_blocks_until_stage_complete(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'artifact-incomplete.db'}")

    with TestClient(app) as client:
        register_and_login(client, "ARTIFACT-INCOMPLETE", "incomplete@example.com")
        paper_stage_id = create_quest_with_paper_stage(client)

        response = client.get(
            f"/stages/{paper_stage_id}/artifacts/english_research_brief_markdown/download"
        )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Paper & Meeting Writer must complete before Markdown artifacts can be downloaded."
    )


def test_download_paper_markdown_artifact_rejects_other_users_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'artifact-permission.db'}")

    with TestClient(app) as client:
        register_and_login(client, "ARTIFACT-OWNER", "owner@example.com")
        paper_stage_id = create_quest_with_paper_stage(client)
        complete_paper_stage_with_artifacts(client, paper_stage_id)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "ARTIFACT-OTHER", "other@example.com")

        response = client.get(
            f"/stages/{paper_stage_id}/artifacts/meeting_outline_markdown/download"
        )

    assert response.status_code == 403
