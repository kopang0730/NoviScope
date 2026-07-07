from fastapi.testclient import TestClient

from noviscope.main import create_app


def test_literature_source_policy_endpoint_exposes_recency_and_reliability(
    tmp_path,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-source-policy.db'}")

    with TestClient(app) as client:
        # Given: the frontend needs to explain Literature Scout evidence quality.

        # When: it asks for the static source policy contract.
        response = client.get("/literature/source-policy")

    # Then: the API exposes the real Literature Scout retrieval and ranking policy.
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "2026-07-literature-source-policy-v1"
    assert body["primary_source"] == {
        "display_name": "OpenAlex Works API",
        "max_results_per_run": 8,
        "source_id": "openalex_works_api",
    }
    assert body["recency_policy"] == {
        "lookback_years": 5,
        "older_than_lookback_guidance": (
            "Older papers can be useful background, but should not dominate novelty claims."
        ),
        "recent_priority_years": 3,
        "recent_score_multiplier": 1.25,
    }
    assert [level["level"] for level in body["reliability_levels"]] == [
        "top_conference_or_journal",
        "peer_reviewed",
        "arxiv_preprint",
        "unknown",
    ]
    assert "cvpr" in body["top_venue_markers"]
    assert "neurips" in body["top_venue_markers"]


def test_literature_source_policy_warns_against_overclaiming_preprints_and_unknowns(
    tmp_path,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-source-cautions.db'}")

    with TestClient(app) as client:
        response = client.get("/literature/source-policy")

    body = response.json()
    levels = {level["level"]: level for level in body["reliability_levels"]}
    assert levels["top_conference_or_journal"]["evidence_strength"] == "strong"
    assert levels["top_conference_or_journal"]["requires_human_review"] is True
    assert "verify the full paper" in levels["top_conference_or_journal"]["citation_guidance"]
    assert levels["arxiv_preprint"]["evidence_strength"] == "low"
    assert levels["arxiv_preprint"]["requires_human_review"] is True
    assert "not be treated as peer-reviewed evidence" in levels["arxiv_preprint"][
        "citation_guidance"
    ]
    assert levels["unknown"]["evidence_strength"] == "unknown"
    assert body["human_review_required"] is True
    assert body["anti_hallucination_rules"] == [
        "Do not invent papers, venues, DOI values, arXiv identifiers, metrics, or conclusions.",
        (
            "If OpenAlex returns no matching works, show an empty result and state "
            "that nothing was found."
        ),
        (
            "Treat metadata as a discovery aid; verify the original PDF or publisher "
            "page before citing."
        ),
    ]
