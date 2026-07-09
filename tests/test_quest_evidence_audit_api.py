from fastapi.testclient import TestClient
from pydantic import JsonValue
from quest_evidence_audit_test_support import (
    add_approved_evidence_auditor_stage,
    set_server_paper_stage,
)

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
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


def create_quest_with_stage_map(client: TestClient) -> tuple[str, dict[str, str]]:
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
    stage_ids = {
        stage["agent_id"]: stage["id"] for stage in stages_response.json()["stages"]
    }
    return quest_id, stage_ids


def complete_stage(
    client: TestClient,
    stage_id: str,
    payload: dict[str, JsonValue],
) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={**payload, "status": "complete"},
    )
    assert complete_response.status_code == 200


def complete_research_gates(
    client: TestClient,
    stage_ids: dict[str, str],
    *,
    database_url: str,
    paper_approved: bool,
    verified_result: bool,
) -> None:
    complete_stage(
        client,
        stage_ids[DEMAND_VALIDATOR_AGENT_ID],
        {
            "evidence_payload": {
                "human_demand_sources": ["Coach interview: shuttle training review"],
                "human_demand_verdict": "verified",
            },
            "human_approved": True,
            "output_payload": {
                "confidence": "medium",
                "demand_assessment": "plausible",
                "evidence_for_demand": ["Coach interview: shuttle training review"],
            },
            "summary": "Demand has a real training scenario.",
        },
    )
    complete_stage(
        client,
        stage_ids[LITERATURE_SCOUT_AGENT_ID],
        {
            "output_payload": {
                "papers": [
                    {
                        "doi": "10.1234/badminton.2026",
                        "paper_ref": "https://openalex.org/W123",
                        "title": "Badminton action benchmark",
                    }
                ],
                "source_policy": "openalex_metadata",
            },
            "summary": "Found one relevant paper.",
        },
    )
    complete_stage(
        client,
        stage_ids[IDEA_GENERATOR_AGENT_ID],
        {
            "evidence_payload": {
                "human_selected_idea_ids": ["idea_temporal_consistency"],
                "selected_idea_count": 1,
            },
            "human_approved": True,
            "output_payload": {
                "ideas": [
                    {
                        "idea_id": "idea_temporal_consistency",
                        "idea_title": "Temporal consistency for action recognition",
                    }
                ],
                "selected_idea_ids": ["idea_temporal_consistency"],
            },
            "summary": "Selected one evidence-linked idea.",
        },
    )
    experiment_results: list[dict[str, JsonValue]] = []
    if verified_result:
        experiment_results.append(
            {
                "artifact_uri": "/data/noviscope/runs/run-001/metrics.json",
                "baseline_name": "Pose-based action classifier",
                "dataset_name": "Badminton clips v1",
                "metric_name": "Action classification accuracy",
                "metric_unit": "%",
                "metric_value": 78.4,
                "result_status": "verified",
                "run_id": "run-001",
            }
        )
    complete_stage(
        client,
        stage_ids[EXPERIMENT_PLANNER_AGENT_ID],
        {
            "human_approved": True,
            "output_payload": {
                "confidence": "medium",
                "data_availability_status": "ready",
                "experiment_results": experiment_results,
                "first_runnable_script_plan": ["Run baseline inference."],
                "metrics": ["Action classification accuracy"],
                "summary": "Experiment plan approved.",
            },
            "summary": "Experiment plan approved.",
        },
    )
    paper_output: dict[str, JsonValue] = {
        "chinese_research_brief_markdown": "# 中文研究 Brief\n\n已验证内容。",
        "confidence": "medium",
        "english_research_brief_markdown": "# Research Brief\n\nVerified content.",
        "human_review_required": [],
        "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\n## Results",
        "meeting_outline_markdown": "# Group Meeting Outline\n\n1. Evidence",
        "verified_facts": ["A coach feedback scenario exists."],
    }
    if verified_result:
        verified_fact = (
            "Verified experiment result: Action classification accuracy = 78.4% "
            "on Badminton clips v1 using Pose-based action classifier "
            "(run run-001; artifact /data/noviscope/runs/run-001/metrics.json)."
        )
        paper_output["verified_facts"] = [verified_fact]
        for artifact_key in (
            "chinese_research_brief_markdown",
            "english_research_brief_markdown",
            "ieee_paper_skeleton_markdown",
            "meeting_outline_markdown",
        ):
            paper_output[artifact_key] = f"{paper_output[artifact_key]}\n\n- {verified_fact}"
    else:
        paper_output["experiment_results_not_available"] = [
            "No verified experiment results are available yet."
        ]
    set_server_paper_stage(
        database_url,
        stage_ids[PAPER_MEETING_WRITER_AGENT_ID],
        paper_output,
        human_approved=paper_approved,
    )


def test_evidence_audit_blocks_draft_quest(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'evidence-audit-draft.db'}")
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-DRAFT", "audit-draft@example.com")
        quest_id, _ = create_quest_with_stage_map(client)

        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert response.status_code == 200
    body = response.json()
    assert body["audit_status"] == "blocked"
    issue_codes = {issue["code"] for issue in body["blocking_issues"]}
    assert issue_codes == {
        "demand_not_approved",
        "evidence_audit_not_approved",
        "experiment_plan_not_approved",
        "idea_not_selected",
        "literature_not_complete",
        "paper_draft_not_generated",
    }
    assert body["ready_for_formal_claims"] is False


def test_evidence_audit_flags_missing_experiment_results_for_review(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'evidence-audit-review.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-REVIEW", "audit-review@example.com")
        quest_id, stage_ids = create_quest_with_stage_map(client)
        complete_research_gates(
            client,
            stage_ids,
            database_url=database_url,
            paper_approved=False,
            verified_result=False,
        )
        add_approved_evidence_auditor_stage(database_url, quest_id)

        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert response.status_code == 200
    body = response.json()
    assert body["audit_status"] == "blocked"
    assert {item["code"] for item in body["blocking_issues"]} == {
        "experiment_results_missing"
    }
    review_codes = {item["code"] for item in body["review_items"]}
    assert review_codes == {"paper_draft_needs_review"}
    assert body["ready_for_formal_claims"] is False
