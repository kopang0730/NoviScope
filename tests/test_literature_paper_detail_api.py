from fastapi.testclient import TestClient
from literature_stage_helpers import (
    complete_literature_stage,
    create_quest_with_literature_stage,
    register_and_login,
)

from noviscope.agents.literature_scout import OPENALEX_SOURCE
from noviscope.main import create_app


def test_literature_paper_detail_returns_saved_source_context(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-paper-detail.db'}")

    with TestClient(app) as client:
        # Given a completed Literature Scout stage with a saved OpenAlex paper.
        register_and_login(client, "PAPER-DETAIL", "paper-detail@example.com")
        literature_stage_id = create_quest_with_literature_stage(client)
        complete_literature_stage(client, literature_stage_id)

        # When the owner opens the detail drawer for that exact paper reference.
        response = client.get(
            f"/stages/{literature_stage_id}/literature-papers/detail",
            params={"paper_ref": "https://openalex.org/W2"},
        )

    # Then the API returns the paper plus review warnings and retrieval context.
    assert response.status_code == 200
    body = response.json()
    assert body["stage_id"] == literature_stage_id
    assert body["paper_ref"] == "https://openalex.org/W2"
    assert body["source"] == OPENALEX_SOURCE
    assert body["search_query"] == "Badminton action recognition"
    assert body["score_basis"] == "OpenAlex relevance_score with a recency boost."
    assert body["unavailable_reason"] == ""
    assert body["paper"]["title"] == "Badminton action recognition benchmark"
    assert body["paper"]["arxiv_id"] == "2401.01234"
    assert body["paper"]["limitations"] == ["Verify full text before citing."]
    assert body["paper"]["source_quality_signals"] == ["Venue matched CVPR."]
    assert body["review_warnings"] == [
        "Verify full text before citing.",
        "Verify the URL, DOI, venue, and year against the publisher or index page.",
        "Treat OpenAlex metadata as retrieval evidence, not as a full-paper review.",
    ]


def test_literature_paper_detail_marks_incomplete_stage_unavailable(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-paper-detail-pending.db'}")

    with TestClient(app) as client:
        # Given a Literature Scout stage before retrieval has completed.
        register_and_login(client, "PAPER-DETAIL-PENDING", "paper-detail-pending@example.com")
        literature_stage_id = create_quest_with_literature_stage(client)

        # When the owner tries to open a paper detail.
        response = client.get(
            f"/stages/{literature_stage_id}/literature-papers/detail",
            params={"paper_ref": "https://openalex.org/W2"},
        )

    # Then the API returns an explicit empty detail state without inventing metadata.
    assert response.status_code == 200
    body = response.json()
    assert body["paper_ref"] == "https://openalex.org/W2"
    assert body["paper"] is None
    assert body["review_warnings"] == []
    assert body["unavailable_reason"] == (
        "Literature Scout must complete before paper details are available."
    )


def test_literature_paper_detail_rejects_unknown_paper_ref(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-paper-detail-missing.db'}")

    with TestClient(app) as client:
        # Given a completed Literature Scout stage with two saved papers.
        register_and_login(client, "PAPER-DETAIL-MISSING", "paper-detail-missing@example.com")
        literature_stage_id = create_quest_with_literature_stage(client)
        complete_literature_stage(client, literature_stage_id)

        # When the owner asks for a paper reference that was not retrieved.
        response = client.get(
            f"/stages/{literature_stage_id}/literature-papers/detail",
            params={"paper_ref": "https://openalex.org/UNKNOWN"},
        )

    # Then the API rejects the stale or fabricated paper reference.
    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]


def test_literature_paper_detail_rejects_other_users_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-paper-detail-permission.db'}")

    with TestClient(app) as client:
        # Given one user owns a completed Literature Scout stage.
        register_and_login(client, "PAPER-DETAIL-OWNER", "paper-detail-owner@example.com")
        literature_stage_id = create_quest_with_literature_stage(client)
        complete_literature_stage(client, literature_stage_id)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "PAPER-DETAIL-OTHER", "paper-detail-other@example.com")

        # When another user asks for the detail.
        response = client.get(
            f"/stages/{literature_stage_id}/literature-papers/detail",
            params={"paper_ref": "https://openalex.org/W2"},
        )

    # Then ownership rules prevent cross-user paper metadata access.
    assert response.status_code == 403
