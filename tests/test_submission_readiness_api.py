from fastapi.testclient import TestClient

from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
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


def create_quest(client: TestClient) -> JsonObject:
    response = client.post(
        "/quests",
        json={
            "initial_direction": "Use computer vision for badminton trajectory recognition.",
            "title": "Badminton trajectory recognition",
        },
    )
    assert response.status_code == 201
    return response.json()


def stages_by_agent(client: TestClient, quest_id: str) -> dict[str, JsonObject]:
    response = client.get(f"/quests/{quest_id}/stages")
    assert response.status_code == 200
    stages = response.json()["stages"]
    assert isinstance(stages, list)
    return {
        stage["agent_id"]: stage
        for stage in stages
        if isinstance(stage, dict) and isinstance(stage.get("agent_id"), str)
    }


def complete_stage(client: TestClient, stage_id: str, payload: JsonObject) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={**payload, "status": "complete"},
    )
    assert complete_response.status_code == 200


def make_review_ready_draft(client: TestClient, quest_id: str) -> None:
    stages = stages_by_agent(client, quest_id)
    complete_stage(
        client,
        str(stages[DEMAND_VALIDATOR_AGENT_ID]["id"]),
        {
            "evidence_payload": {
                "human_demand_sources": ["Coach feedback interview"],
                "human_demand_verdict": "verified",
                "requires_human_review": True,
            },
            "human_approved": True,
            "output_payload": {
                "confidence": "medium",
                "demand_assessment": "plausible",
                "evidence_for_demand": ["Coach feedback interview"],
            },
            "review_notes": "Human reviewer verified the training scenario.",
            "summary": "Demand has a real training scenario.",
        },
    )
    complete_stage(
        client,
        str(stages[EXPERIMENT_PLANNER_AGENT_ID]["id"]),
        {
            "human_approved": True,
            "output_payload": {
                "confidence": "medium",
                "datasets_needed": ["Training videos with shuttle annotations"],
                "metrics": ["trajectory localization error"],
                "summary": "Experiment plan is ready for human review.",
            },
            "review_notes": "Plan is feasible, but no GPU run has executed.",
            "summary": "Experiment plan is ready.",
        },
    )
    complete_stage(
        client,
        str(stages[PAPER_MEETING_WRITER_AGENT_ID]["id"]),
        {
            "human_approved": True,
            "output_payload": {
                "chinese_research_brief_markdown": "# 中文研究 Brief\n\n## 已验证事实",
                "confidence": "medium",
                "english_research_brief_markdown": "# Research Brief\n\n## Verified Facts",
                "experiment_results_not_available": ["No training run has been executed."],
                "human_review_required": ["Review claims before group meeting."],
                "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\n## Results\nTBD.",
                "meeting_outline_markdown": "# Group Meeting Outline\n\n1. Motivation",
                "model_generated_hypotheses": ["Temporal consistency may reduce jitter."],
                "verified_facts": ["A coach feedback scenario exists."],
            },
            "review_notes": "Draft can support discussion, not formal submission.",
            "summary": "Generated review-only writing artifacts.",
        },
    )


def test_submission_readiness_requires_authentication(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'submission-auth.db'}")

    with TestClient(app) as client:
        response = client.get("/quests/quest_missing/submission-readiness")

    assert response.status_code == 401


def test_submission_readiness_blocks_empty_quest(
    dev_admin_header_enabled: None,
    tmp_path,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'submission-empty.db'}")

    with TestClient(app) as client:
        register_and_login(client, "SUBMISSION-EMPTY", "submission-empty@example.com")
        quest = create_quest(client)
        response = client.get(f"/quests/{quest['id']}/submission-readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["quest_id"] == quest["id"]
    assert body["overall_status"] == "blocked"
    assert body["can_use_for_meeting"] is False
    assert body["can_use_for_formal_submission"] is False
    assert body["available_artifact_count"] == 0
    assert body["complete_stage_count"] == 0
    assert "Paper & Meeting Writer is not complete." in body["formal_submission_blockers"]
    paper_check = next(
        check
        for check in body["stage_checks"]
        if check["agent_id"] == PAPER_MEETING_WRITER_AGENT_ID
    )
    assert paper_check["ready_for_submission"] is False
    assert paper_check["blocking_reasons"] == ["stage_not_complete"]


def test_submission_readiness_allows_review_packet_but_blocks_formal_submission(
    dev_admin_header_enabled: None,
    tmp_path,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'submission-review.db'}")

    with TestClient(app) as client:
        register_and_login(client, "SUBMISSION-REVIEW", "submission-review@example.com")
        quest = create_quest(client)
        make_review_ready_draft(client, str(quest["id"]))
        response = client.get(f"/quests/{quest['id']}/submission-readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "review_ready"
    assert body["can_use_for_meeting"] is True
    assert body["can_use_for_formal_submission"] is False
    assert body["available_artifact_count"] == 4
    assert body["complete_stage_count"] == 3
    assert "Experiment results are not available." in body["formal_submission_blockers"]
    assert "Paper draft still has human-review items." in body["formal_submission_blockers"]
    assert body["review_warnings"] == [
        "Experiment results are not available; do not present draft as validated results.",
        "Paper draft still has human-review items.",
    ]
    paper_check = next(
        check
        for check in body["stage_checks"]
        if check["agent_id"] == PAPER_MEETING_WRITER_AGENT_ID
    )
    assert paper_check["ready_for_submission"] is False
    assert paper_check["blocking_reasons"] == [
        "experiment_results_not_available",
        "paper_human_review_required",
    ]
