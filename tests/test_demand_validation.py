import json

from pydantic import SecretStr

from noviscope.agents.demand_validation import (
    DemandValidationRequest,
    build_chat_completion_payload,
    parse_demand_validation_output,
)
from noviscope.models.provider import ProviderKind


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


def test_build_chat_completion_payload_treats_user_sources_as_unverified_leads() -> None:
    request = DemandValidationRequest(
        api_key=SecretStr("test-key"),
        base_url="https://example.invalid/v1",
        initial_direction=(
            "# NoviScope Quest Intake\n"
            "- Research direction: Handwritten text erasure.\n"
            "- Demand evidence sources to verify: Partner sample scans; customer note."
        ),
        model="test-model",
        provider_id="provider-1",
        provider_kind=ProviderKind.OPENAI_COMPATIBLE,
        provider_name="Test Provider",
        quest_title="Handwritten text erasure",
        stage_id="stage-1",
    )

    payload = build_chat_completion_payload(request)

    system_prompt = payload["messages"][0]["content"]
    user_prompt = payload["messages"][1]["content"]
    assert "Treat user-provided demand evidence sources as unverified leads" in system_prompt
    assert "Demand evidence sources to verify: Partner sample scans" in user_prompt
