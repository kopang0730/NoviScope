import json

import httpx
from pydantic import SecretStr

from noviscope.agents.demand_validation import (
    DemandValidationRequest,
    DemandValidationStageRunner,
    OpenAICompatibleDemandValidationRunner,
    build_chat_completion_payload,
    parse_demand_validation_output,
)
from noviscope.agents.provider_chat import DEFAULT_MAX_TOKENS, ProviderChatClient
from noviscope.core.stage_policy import NO_EXTERNAL_VERIFICATION_RISK
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


def test_parse_demand_validation_output_deduplicates_external_verification_risk() -> None:
    response = {
        "confidence": "high",
        "demand_assessment": "strong",
        "evidence_for_demand": ["The prompt names a plausible coaching workflow."],
        "go_or_no_go_recommendation": "go_with_human_review",
        "missing_evidence": ["No external customer source has been checked."],
        "next_step": "Ask a human reviewer to verify demand evidence.",
        "real_world_scenario": "Badminton training feedback.",
        "risks": [NO_EXTERNAL_VERIFICATION_RISK],
        "suggested_human_checklist": ["Confirm dataset ownership."],
        "summary": "Plausible demand, but external evidence is still missing.",
        "target_user_or_customer": "Badminton coaches.",
    }

    output = parse_demand_validation_output(json.dumps(response))

    assert output.confidence == "medium"
    assert output.risks == [NO_EXTERNAL_VERIFICATION_RISK]


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


def test_demand_validation_stage_runner_supports_anthropic_provider() -> None:
    stage_runner = DemandValidationStageRunner(OpenAICompatibleDemandValidationRunner())

    assert ProviderKind.ANTHROPIC in stage_runner.supported_provider_kinds


def test_demand_validation_runner_executes_anthropic_messages_api() -> None:
    captured_payload: dict[str, object] = {}
    model_response = {
        "confidence": "medium",
        "demand_assessment": "plausible",
        "evidence_for_demand": ["The prompt names a concrete coaching workflow."],
        "go_or_no_go_recommendation": "go_with_human_review",
        "missing_evidence": ["No external customer source has been verified."],
        "next_step": "Ask the user to verify real demand evidence before experiments.",
        "real_world_scenario": "Badminton training feedback.",
        "risks": ["The demand evidence is still self-reported."],
        "suggested_human_checklist": ["Confirm data ownership and annotation availability."],
        "summary": "Plausible demand, but external evidence is still missing.",
        "target_user_or_customer": "Badminton coaches.",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == httpx.URL("https://api.anthropic.com/v1/messages")
        assert request.headers["x-api-key"] == "test-key"
        assert request.headers["anthropic-version"] == "2023-06-01"
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"content": [{"text": json.dumps(model_response), "type": "text"}]},
        )

    runner = OpenAICompatibleDemandValidationRunner(
        chat_client=ProviderChatClient(
            client_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler))
        )
    )

    output = runner.run(
        DemandValidationRequest(
            api_key=SecretStr("test-key"),
            base_url="https://api.anthropic.com/v1",
            initial_direction="Use computer vision to recognize badminton action quality.",
            model="claude-test-model",
            provider_id="provider-anthropic",
            provider_kind=ProviderKind.ANTHROPIC,
            provider_name="Anthropic",
            quest_title="Badminton action recognition",
            stage_id="stage-1",
        )
    )

    assert output.summary == "Plausible demand, but external evidence is still missing."
    assert captured_payload["model"] == "claude-test-model"
    assert captured_payload["max_tokens"] == DEFAULT_MAX_TOKENS
    assert "temperature" not in captured_payload
    assert isinstance(captured_payload["system"], str)
    assert "NoviScope's Demand Validator" in captured_payload["system"]
    messages = captured_payload["messages"]
    assert isinstance(messages, list)
    assert messages[0]["role"] == "user"
    assert "Badminton action recognition" in messages[0]["content"]
