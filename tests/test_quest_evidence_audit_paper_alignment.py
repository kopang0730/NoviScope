from fastapi.testclient import TestClient
from quest_evidence_audit_test_support import (
    add_trusted_code_result_stage,
    set_server_paper_stage,
)
from test_quest_evidence_audit_api import register_and_login
from test_quest_evidence_audit_trust import create_ready_quest, review_codes

from noviscope.core.stage_policy import PAPER_MEETING_WRITER_AGENT_ID
from noviscope.main import create_app

TRUSTED_RESULT_FACT = (
    "Verified experiment result: Action classification accuracy = 78.4% "
    "on Badminton clips v1 using Pose-based action classifier "
    "(run run-001; artifact /data/noviscope/runs/run-001/metrics.json)."
)


def test_public_paper_output_mutation_is_rejected(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-stale-approval.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-STALE-APPROVAL", "audit-stale-approval@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        add_trusted_code_result_stage(database_url, quest_id)
        patch_response = client.patch(
            f"/stages/{stage_ids[PAPER_MEETING_WRITER_AGENT_ID]}",
            json={
                "output_payload": {
                    "chinese_research_brief_markdown": "# Mutated",
                    "english_research_brief_markdown": "# Mutated",
                    "ieee_paper_skeleton_markdown": "# Mutated",
                    "meeting_outline_markdown": "# Mutated",
                    "verified_facts": [TRUSTED_RESULT_FACT],
                }
            },
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 400
    body = response.json()
    assert body["ready_for_formal_claims"] is True


def test_audit_rejects_a_stale_no_results_paper(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-stale-paper.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-STALE-PAPER", "audit-stale@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        add_trusted_code_result_stage(database_url, quest_id)
        set_server_paper_stage(
            database_url,
            stage_ids[PAPER_MEETING_WRITER_AGENT_ID],
            {
                "chinese_research_brief_markdown": "# 中文研究 Brief",
                "english_research_brief_markdown": "# Research Brief",
                "experiment_results_not_available": ["No verified results are available."],
                "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\n## Results\nTBD.",
                "meeting_outline_markdown": "# Group Meeting Outline",
                "verified_facts": [],
            },
            human_approved=True,
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "paper_results_not_aligned" in review_codes(body)


def test_audit_rejects_a_verified_fact_for_a_different_run(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-mismatched-result.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-MISMATCHED-RESULT", "audit-mismatch@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        add_trusted_code_result_stage(database_url, quest_id)
        set_server_paper_stage(
            database_url,
            stage_ids[PAPER_MEETING_WRITER_AGENT_ID],
            {
                "chinese_research_brief_markdown": "# 中文研究 Brief",
                "english_research_brief_markdown": "# Research Brief",
                "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton",
                "meeting_outline_markdown": "# Group Meeting Outline",
                "verified_facts": [
                    "Verified experiment result: Accuracy = 99% "
                    "(run unrelated-run; artifact /tmp/unrelated.json)."
                ],
            },
            human_approved=True,
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "paper_results_not_aligned" in review_codes(body)


def test_audit_rejects_a_run_id_that_only_contains_the_trusted_id(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-run-id-boundary.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-RUN-BOUNDARY", "audit-boundary@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        add_trusted_code_result_stage(database_url, quest_id)
        set_server_paper_stage(
            database_url,
            stage_ids[PAPER_MEETING_WRITER_AGENT_ID],
            {
                "chinese_research_brief_markdown": "# 中文研究 Brief",
                "english_research_brief_markdown": "# Research Brief",
                "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton",
                "meeting_outline_markdown": "# Group Meeting Outline",
                "verified_facts": [
                    "Verified experiment result: Action classification accuracy = 78.4% "
                    "(run run-001-extra; artifact "
                    "/data/noviscope/runs/run-001/metrics.json)."
                ],
            },
            human_approved=True,
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "paper_results_not_aligned" in review_codes(body)


def test_audit_rejects_forged_claims_in_downloadable_artifacts(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-forged-artifacts.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-FORGED-ARTIFACTS", "audit-forged@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        add_trusted_code_result_stage(database_url, quest_id)
        forged_fact = (
            "Verified experiment result: Action classification accuracy = 99.9% "
            "on Badminton clips v1 using Pose-based action classifier "
            "(run forged-run; artifact /tmp/forged-metrics.json)."
        )
        forged_artifact = f"# Results\n\n- {TRUSTED_RESULT_FACT}\n- {forged_fact}"
        set_server_paper_stage(
            database_url,
            stage_ids[PAPER_MEETING_WRITER_AGENT_ID],
            {
                "chinese_research_brief_markdown": forged_artifact,
                "english_research_brief_markdown": forged_artifact,
                "ieee_paper_skeleton_markdown": forged_artifact,
                "meeting_outline_markdown": forged_artifact,
                "verified_facts": [TRUSTED_RESULT_FACT],
            },
            human_approved=True,
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "paper_results_not_aligned" in review_codes(body)


def test_audit_requires_every_trusted_result_in_the_paper(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-missing-trusted-result.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-ALL-RESULTS", "audit-all-results@example.com")
        quest_id, _ = create_ready_quest(client, database_url)
        add_trusted_code_result_stage(database_url, quest_id)
        add_trusted_code_result_stage(
            database_url,
            quest_id,
            {
                "artifact_uri": "/data/noviscope/runs/run-002/metrics.json",
                "baseline_name": "Pose-based action classifier",
                "dataset_name": "Badminton clips v1",
                "metric_name": "Macro F1",
                "metric_unit": "%",
                "metric_value": 76.2,
                "result_status": "verified",
                "run_id": "run-002",
            },
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "paper_results_not_aligned" in review_codes(body)
