from fastapi.testclient import TestClient
from literature_stage_helpers import (
    complete_literature_stage,
    create_quest_with_literature_stage,
    register_and_login,
)

from noviscope.agents.literature_scout import OPENALEX_SOURCE
from noviscope.main import create_app


def test_literature_paper_table_filters_and_sorts_saved_papers(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-paper-table.db'}")

    with TestClient(app) as client:
        # Given a completed Literature Scout stage with saved OpenAlex paper metadata.
        register_and_login(client, "PAPER-TABLE", "paper-table@example.com")
        literature_stage_id = create_quest_with_literature_stage(client)
        complete_literature_stage(client, literature_stage_id)

        # When the owner asks for a top-venue table sorted by publication year.
        response = client.get(
            f"/stages/{literature_stage_id}/literature-papers",
            params={
                "reliability_level": "top_conference_or_journal",
                "sort": "year_desc",
            },
        )

    # Then the API returns only saved matching papers and source context.
    assert response.status_code == 200
    body = response.json()
    assert body["stage_id"] == literature_stage_id
    assert body["source"] == OPENALEX_SOURCE
    assert body["search_query"] == "Badminton action recognition"
    assert body["total_count"] == 2
    assert body["returned_count"] == 1
    assert body["filters"] == {"reliability_level": "top_conference_or_journal"}
    assert [paper["title"] for paper in body["papers"]] == [
        "Badminton action recognition benchmark"
    ]
    paper = body["papers"][0]
    assert paper["paper_ref"] == "https://openalex.org/W2"
    assert paper["authors"] == ["Ada Chen", "Bo Lin"]
    assert paper["year"] == 2025
    assert paper["venue"] == "CVPR"
    assert paper["relevance_score"] == 112.5
    assert paper["source_quality_signals"] == ["Venue matched CVPR."]


def test_literature_paper_table_marks_incomplete_stage_unavailable(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-paper-pending.db'}")

    with TestClient(app) as client:
        # Given a Literature Scout stage with no retrieved papers yet.
        register_and_login(client, "PAPER-TABLE-PENDING", "paper-pending@example.com")
        literature_stage_id = create_quest_with_literature_stage(client)

        # When the owner asks for table rows.
        response = client.get(f"/stages/{literature_stage_id}/literature-papers")

    # Then the API gives an explicit empty table state without inventing papers.
    assert response.status_code == 200
    body = response.json()
    assert body["stage_id"] == literature_stage_id
    assert body["source"] == ""
    assert body["search_query"] == ""
    assert body["total_count"] == 0
    assert body["returned_count"] == 0
    assert body["papers"] == []
    assert body["unavailable_reason"] == (
        "Literature Scout must complete before paper table rows are available."
    )


def test_literature_paper_table_rejects_other_users_stage(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-paper-permission.db'}")

    with TestClient(app) as client:
        # Given one user owns a completed Literature Scout stage.
        register_and_login(client, "PAPER-TABLE-OWNER", "paper-owner@example.com")
        literature_stage_id = create_quest_with_literature_stage(client)
        complete_literature_stage(client, literature_stage_id)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        register_and_login(client, "PAPER-TABLE-OTHER", "paper-other@example.com")

        # When another user asks for those paper rows.
        response = client.get(f"/stages/{literature_stage_id}/literature-papers")

    # Then ownership rules prevent cross-user paper metadata access.
    assert response.status_code == 403
