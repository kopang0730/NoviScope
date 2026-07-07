from fastapi.testclient import TestClient

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.api.evidence_ledger import build_quest_evidence_ledger
from noviscope.core.stage_policy import DEMAND_VALIDATOR_AGENT_ID
from noviscope.main import create_app
from noviscope.models.quest import StageCard, StageStatus

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


def create_traceable_quest(client: TestClient) -> tuple[str, str, str]:
    quest_response = client.post(
        "/quests",
        json={
            "initial_direction": ("Erase handwritten answers from scanned worksheets for reuse."),
            "title": "Handwritten text erasure",
        },
    )
    assert quest_response.status_code == 201
    quest_id = quest_response.json()["id"]
    stages_response = client.get(f"/quests/{quest_id}/stages")
    assert stages_response.status_code == 200
    stages = stages_response.json()["stages"]
    demand_stage = next(stage for stage in stages if stage["agent_id"] == DEMAND_VALIDATOR_AGENT_ID)
    literature_stage = next(
        stage for stage in stages if stage["agent_id"] == LITERATURE_SCOUT_AGENT_ID
    )
    return quest_id, demand_stage["id"], literature_stage["id"]


def complete_traceable_demand_stage(client: TestClient, stage_id: str) -> None:
    running_response = client.patch(f"/stages/{stage_id}", json={"status": "running"})
    assert running_response.status_code == 200
    complete_response = client.patch(
        f"/stages/{stage_id}",
        json={
            "evidence_payload": {
                "provider_id": "provider_123",
                "provider_model": "gpt-test",
                "requires_human_review": True,
                "source_policy": "model_only_no_external_source_verification",
                "sources": ["worksheet vendor interview", "sample worksheet batch"],
            },
            "human_approved": False,
            "output_payload": {
                "confidence": "medium",
                "evidence_for_demand": ["worksheet vendor interview"],
                "risks": ["External source verification is still missing."],
            },
            "review_notes": "Need a human to verify the vendor scenario.",
            "status": "complete",
            "summary": "Plausible demand, but source verification is incomplete.",
        },
    )
    assert complete_response.status_code == 200


def test_quest_evidence_ledger_lists_traceable_stage_entries() -> None:
    # Given: a Quest workflow with one completed stage containing model evidence.
    demand_stage = StageCard(
        agent_id="demand_validator",
        evidence_payload={
            "provider_id": "provider_123",
            "provider_model": "gpt-test",
            "requires_human_review": True,
            "source_policy": "model_only_no_external_source_verification",
            "sources": ["teacher interview", "company scenario"],
        },
        human_approved=False,
        id="stage_demand",
        output_payload={
            "confidence": "medium",
            "evidence_for_demand": ["company scenario"],
            "risks": ["External source verification is still missing."],
        },
        quest_id="quest_trace",
        review_notes="Need a human to verify the company scenario.",
        status=StageStatus.COMPLETE,
        summary="Plausible demand, but source verification is incomplete.",
        title="Demand validation",
    )
    literature_stage = StageCard(
        agent_id="literature_scout",
        id="stage_literature",
        quest_id="quest_trace",
        status=StageStatus.PENDING,
        summary="Waiting for demand review.",
        title="Literature scout",
    )

    # When: the frontend asks for a Quest-level evidence ledger.
    ledger = build_quest_evidence_ledger(
        "quest_trace",
        [demand_stage, literature_stage],
    )

    # Then: the ledger exposes audit-ready evidence metadata without guessing.
    assert ledger.quest_id == "quest_trace"
    assert ledger.total_stage_count == 2
    assert ledger.evidence_entry_count == 1
    assert ledger.requires_human_review_count == 1
    assert ledger.missing_evidence_count == 1
    assert ledger.entries[0].model_dump(mode="json") == {
        "agent_id": "demand_validator",
        "confidence": "medium",
        "evidence_keys": [
            "provider_id",
            "provider_model",
            "requires_human_review",
            "source_policy",
            "sources",
        ],
        "human_approved": False,
        "output_keys": ["confidence", "evidence_for_demand", "risks"],
        "provider_id": "provider_123",
        "provider_model": "gpt-test",
        "requires_human_review": True,
        "review_notes": "Need a human to verify the company scenario.",
        "source_count": 2,
        "source_policy": "model_only_no_external_source_verification",
        "source_refs": ["company scenario", "teacher interview"],
        "stage_id": "stage_demand",
        "stage_status": "complete",
        "stage_title": "Demand validation",
        "summary": "Plausible demand, but source verification is incomplete.",
    }


def test_evidence_ledger_endpoint_returns_saved_stage_evidence(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'evidence-ledger.db'}")

    with TestClient(app) as client:
        # Given: a Quest with one completed evidence-bearing stage and one pending stage.
        register_and_login(client, "EVIDENCE-LEDGER", "evidence-ledger@example.com")
        quest_id, demand_stage_id, literature_stage_id = create_traceable_quest(client)
        complete_traceable_demand_stage(client, demand_stage_id)

        # When: the frontend requests the Quest evidence ledger.
        response = client.get(f"/quests/{quest_id}/evidence-ledger")

    # Then: the API returns saved evidence metadata without inventing pending sources.
    assert response.status_code == 200
    body = response.json()
    assert body["quest_id"] == quest_id
    assert body["total_stage_count"] == 5
    assert body["evidence_entry_count"] == 1
    assert body["missing_evidence_count"] == 4
    assert body["requires_human_review_count"] == 1

    demand_entry = next(entry for entry in body["entries"] if entry["stage_id"] == demand_stage_id)
    assert demand_entry["agent_id"] == DEMAND_VALIDATOR_AGENT_ID
    assert demand_entry["confidence"] == "medium"
    assert demand_entry["provider_id"] == "provider_123"
    assert demand_entry["provider_model"] == "gpt-test"
    assert demand_entry["requires_human_review"] is True
    assert demand_entry["human_approved"] is False
    assert demand_entry["source_policy"] == "model_only_no_external_source_verification"
    assert demand_entry["source_count"] == 2
    assert demand_entry["source_refs"] == [
        "worksheet vendor interview",
        "sample worksheet batch",
    ]
    assert demand_entry["review_notes"] == "Need a human to verify the vendor scenario."

    literature_entry = next(
        entry for entry in body["entries"] if entry["stage_id"] == literature_stage_id
    )
    assert literature_entry["agent_id"] == LITERATURE_SCOUT_AGENT_ID
    assert literature_entry["source_count"] == 0
    assert literature_entry["source_refs"] == []
    assert literature_entry["source_policy"] == "no_evidence_recorded"


def test_download_evidence_ledger_returns_markdown_review_attachment(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'evidence-ledger-download.db'}")

    with TestClient(app) as client:
        # Given: a Quest with reviewable evidence and missing evidence stages.
        register_and_login(
            client,
            "EVIDENCE-LEDGER-DOWNLOAD",
            "evidence-ledger-download@example.com",
        )
        quest_id, demand_stage_id, literature_stage_id = create_traceable_quest(client)
        complete_traceable_demand_stage(client, demand_stage_id)

        # When: the user downloads the evidence ledger for offline review.
        response = client.get(f"/quests/{quest_id}/evidence-ledger/download")

    # Then: the response is a Markdown attachment with traceability metadata.
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="noviscope-evidence-ledger-{quest_id}.md"'
    )
    assert f"# NoviScope Evidence Ledger: {quest_id}" in response.text
    assert "## Trust Summary" in response.text
    assert "- Total stages: 5" in response.text
    assert "- Evidence-bearing stages: 1" in response.text
    assert "- Missing evidence stages: 4" in response.text
    assert "- Stages requiring human review: 1" in response.text
    assert f"### Demand validation (`{demand_stage_id}`)" in response.text
    assert "- Status: complete" in response.text
    assert "- Confidence: medium" in response.text
    assert "- Human approved: No" in response.text
    assert "- Requires human review: Yes" in response.text
    assert "- Provider: provider_123 / gpt-test" in response.text
    assert "- Source policy: model_only_no_external_source_verification" in response.text
    assert "- Source refs: worksheet vendor interview; sample worksheet batch" in response.text
    assert "- Review notes: Need a human to verify the vendor scenario." in response.text
    assert f"### Literature scout (`{literature_stage_id}`)" in response.text
    assert "- Source refs: None recorded" in response.text
