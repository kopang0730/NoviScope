from fastapi.testclient import TestClient

from noviscope.main import create_app


def test_workflow_review_gates_exposes_static_human_gate_contract() -> None:
    app = create_app(database_url="sqlite:///:memory:")

    with TestClient(app) as client:
        # Given

        # When
        response = client.get("/workflow/review-gates")

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "2026-07-review-gates-v1"
    assert [gate["gate_id"] for gate in body["gates"]] == [
        "demand_truth_review",
        "idea_selection_review",
        "experiment_plan_review",
        "paper_artifact_review",
    ]
    demand_gate = body["gates"][0]
    assert demand_gate["source_agent_id"] == "demand_validator"
    assert demand_gate["blocks_agent_ids"] == [
        "literature_scout",
        "idea_generator",
    ]
    assert demand_gate["review_endpoint_template"] == "/stages/{stage_id}/demand-review"
    assert demand_gate["required_evidence"] == [
        "real_world_source",
        "human_verdict",
        "go_or_no_go",
    ]
    assert demand_gate["user_action_label"] == {
        "en": "Review demand evidence",
        "zh": "复核需求真实性",
    }


def test_workflow_review_gates_distinguish_blocking_and_terminal_reviews() -> None:
    app = create_app(database_url="sqlite:///:memory:")

    with TestClient(app) as client:
        # Given

        # When
        response = client.get("/workflow/review-gates")

    # Then
    assert response.status_code == 200
    gates_by_id = {gate["gate_id"]: gate for gate in response.json()["gates"]}
    assert gates_by_id["idea_selection_review"]["blocks_agent_ids"] == [
        "experiment_planner"
    ]
    assert gates_by_id["idea_selection_review"]["review_endpoint_template"] == (
        "/stages/{stage_id}/select-ideas"
    )
    assert gates_by_id["experiment_plan_review"]["blocks_agent_ids"] == [
        "paper_meeting_writer"
    ]
    assert gates_by_id["experiment_plan_review"]["review_endpoint_template"] == (
        "/stages/{stage_id}"
    )
    assert gates_by_id["paper_artifact_review"]["blocks_agent_ids"] == []
    assert gates_by_id["paper_artifact_review"]["terminal_review"] is True
    assert "unverified experiments" in gates_by_id["paper_artifact_review"]["risk_if_skipped"]["en"]
