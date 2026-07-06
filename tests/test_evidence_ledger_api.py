from noviscope.api.evidence_ledger import build_quest_evidence_ledger
from noviscope.models.quest import StageCard, StageStatus


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
