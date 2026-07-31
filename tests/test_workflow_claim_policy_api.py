from fastapi.testclient import TestClient

from noviscope.main import create_app


def test_workflow_claim_policy_exposes_paper_artifact_claim_categories() -> None:
    app = create_app(database_url="sqlite:///:memory:")

    with TestClient(app) as client:
        # Given

        # When
        response = client.get("/workflow/claim-policy")

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "2026-07-claim-policy-v1"
    assert [category["claim_type"] for category in body["categories"]] == [
        "verified_fact",
        "source_supported_claim",
        "model_generated_hypothesis",
        "experiment_result_unavailable",
        "human_review_required",
    ]
    verified_fact = body["categories"][0]
    assert verified_fact["output_field"] == "verified_facts"
    assert verified_fact["allowed_in_artifacts"] == [
        "chinese_research_brief_markdown",
        "english_research_brief_markdown",
        "meeting_outline_markdown",
        "ieee_paper_skeleton_markdown",
    ]
    assert verified_fact["requires_source_reference"] is True
    assert verified_fact["requires_human_review"] is False


def test_workflow_claim_policy_exposes_result_and_hypothesis_guardrails() -> None:
    app = create_app(database_url="sqlite:///:memory:")

    with TestClient(app) as client:
        # Given

        # When
        response = client.get("/workflow/claim-policy")

    # Then
    assert response.status_code == 200
    body = response.json()
    categories_by_type = {
        category["claim_type"]: category for category in body["categories"]
    }
    assert categories_by_type["model_generated_hypothesis"]["output_field"] == (
        "model_generated_hypotheses"
    )
    assert categories_by_type["model_generated_hypothesis"]["requires_human_review"] is True
    assert categories_by_type["experiment_result_unavailable"]["output_field"] == (
        "experiment_results_not_available"
    )
    assert categories_by_type["experiment_result_unavailable"]["requires_source_reference"] is False
    assert "completed benchmark" in body["prohibited_claims"][0]["pattern"]
    assert body["default_result_section_notice"]["en"].startswith(
        "No experiment results are available"
    )
