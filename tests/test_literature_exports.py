from fastapi.testclient import TestClient

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
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


def create_completed_literature_stage(client: TestClient) -> str:
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
    literature_stage = next(
        stage
        for stage in stages_response.json()["stages"]
        if stage["agent_id"] == LITERATURE_SCOUT_AGENT_ID
    )
    running_response = client.patch(
        f"/stages/{literature_stage['id']}",
        json={"status": "running"},
    )
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{literature_stage['id']}",
        json={
            "output_payload": {
                "papers": [
                    {
                        "abstract_summary": "A benchmark for fast badminton rally perception.",
                        "authors": ["Ada Chen", "Grace Lee"],
                        "doi": "https://doi.org/10.1000/badminton",
                        "limitations": [
                            "OpenAlex metadata only; verify the full paper before citing."
                        ],
                        "openalex_id": "https://openalex.org/W123",
                        "publication_type": "proceedings-article",
                        "recency_bucket": "recent_3_years",
                        "relevance_score": 112.5,
                        "reliability_level": "top_conference_or_journal",
                        "source_quality_signals": ["Venue is in the configured top list."],
                        "source_type": "conference",
                        "api_key": "sk-hidden-paper-key",
                        "raw_response": "poisoned primary metadata",
                        "title": "Badminton Vision Benchmark",
                        "url": "https://example.org/badminton-paper",
                        "venue": "CVPR",
                        "why_relevant": "Matches query terms in OpenAlex metadata.",
                        "year": 2025,
                    }
                ],
                "api_key": "sk-hidden-stage-key",
                "raw_response": {"provider_payload": "hidden raw response"},
                "score_basis": "OpenAlex relevance_score with recency boost.",
                "search_query": "badminton trajectory recognition",
                "source": "openalex_works_api",
                "summary": "Found 1 OpenAlex papers for Literature Scout review.",
            },
            "status": "complete",
            "summary": "Found 1 OpenAlex papers for Literature Scout review.",
        },
    )
    assert complete_response.status_code == 200
    return literature_stage["id"]


def test_download_literature_citations_returns_markdown_attachment(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    # Given: an owner has a completed Literature Scout stage with real metadata.
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-citations.db'}")
    with TestClient(app) as client:
        register_and_login(client, "LITERATURE-CITATIONS", "citations@example.com")
        literature_stage_id = create_completed_literature_stage(client)

        # When: the owner downloads the citation list.
        response = client.get(f"/stages/{literature_stage_id}/literature-citations/download")

    # Then: the response is a review-only Markdown bibliography attachment.
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"] == (
        'attachment; filename="literature-scout-citations.md"'
    )
    assert "# NoviScope Literature Citation List" in response.text
    assert "Review OpenAlex metadata against the primary paper before citing." in response.text
    assert "Badminton Vision Benchmark" in response.text
    assert "Ada Chen, Grace Lee" in response.text
    assert "https://doi.org/10.1000/badminton" in response.text
    assert "OpenAlex metadata only" in response.text
    assert "Hidden payload fields" in response.text
    assert "api_key" not in response.text.lower()
    assert "sk-hidden" not in response.text
    assert "poisoned primary metadata" not in response.text
    assert "provider_payload" not in response.text


def test_download_literature_citations_rejects_other_member(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    # Given: one member owns a completed Literature Scout stage.
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-citations-access.db'}")
    with TestClient(app) as client:
        register_and_login(client, "LITERATURE-CITATIONS-OWNER", "owner@example.com")
        literature_stage_id = create_completed_literature_stage(client)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "LITERATURE-CITATIONS-OTHER", "other@example.com")

        # When: another member tries to download the citation list.
        response = client.get(f"/stages/{literature_stage_id}/literature-citations/download")

    # Then: the stage remains protected by quest ownership.
    assert response.status_code == 403


def test_download_literature_citations_rejects_pending_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    # Given: a member owns a Literature Scout stage that has not completed.
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-citations-pending.db'}")
    with TestClient(app) as client:
        register_and_login(client, "LITERATURE-CITATIONS-PENDING", "pending@example.com")
        quest_response = client.post(
            "/quests",
            json={
                "initial_direction": "Use computer vision for badminton trajectory recognition.",
                "title": "Badminton trajectory recognition",
            },
        )
        assert quest_response.status_code == 201
        stages_response = client.get(f"/quests/{quest_response.json()['id']}/stages")
        assert stages_response.status_code == 200
        literature_stage = next(
            stage
            for stage in stages_response.json()["stages"]
            if stage["agent_id"] == LITERATURE_SCOUT_AGENT_ID
        )

        # When: the owner downloads citations before Literature Scout completes.
        response = client.get(f"/stages/{literature_stage['id']}/literature-citations/download")

    # Then: NoviScope does not export placeholder citations.
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Literature Scout must complete before citations can be downloaded."
    )
