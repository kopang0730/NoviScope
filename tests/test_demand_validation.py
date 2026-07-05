import json

from noviscope.agents.demand_validation import parse_demand_validation_output


def test_parse_demand_validation_output_downgrades_high_confidence() -> None:
    response = {
        "confidence": "high",
        "demand_assessment": "strong",
        "evidence_for_demand": ["The prompt names a plausible coaching workflow."],
        "go_or_no_go_recommendation": "go_with_human_review",
        "missing_evidence": ["No external customer source has been checked."],
        "next_step": "Ask a human reviewer to verify demand evidence.",
        "real_world_scenario": "Badminton training feedback.",
        "risks": [],
        "suggested_human_checklist": ["Confirm dataset ownership."],
        "summary": "Plausible demand, but external evidence is still missing.",
        "target_user_or_customer": "Badminton coaches.",
    }

    output = parse_demand_validation_output(json.dumps(response))

    assert output.confidence == "medium"
    assert output.risks == [
        "High confidence was downgraded because no external source verification ran in this "
        "MVP stage.",
    ]
