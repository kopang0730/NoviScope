import json

import httpx
from pydantic import SecretStr

from noviscope.agents.paper_meeting_writer import (
    HUMAN_REVIEW_NOTICE,
    NO_RESULTS_NOTICE,
    OpenAICompatiblePaperMeetingWriterRunner,
    PaperMeetingWriterRequest,
    PaperMeetingWriterStageRunner,
    parse_paper_meeting_writer_output,
)
from noviscope.agents.provider_chat import DEFAULT_MAX_TOKENS, ProviderChatClient
from noviscope.models.provider import ProviderKind


def build_request() -> PaperMeetingWriterRequest:
    return PaperMeetingWriterRequest(
        api_key=SecretStr("sk-test"),
        base_url="https://api.example.com/v1",
        demand_validation={"real_world_scenario": "Coach feedback"},
        experiment_plan={"summary": "Plan baseline and ablations."},
        initial_direction="Badminton action recognition",
        model="example-chat",
        papers=[{"paper_ref": "https://openalex.org/W123", "title": "Badminton benchmark"}],
        provider_id="provider_1",
        provider_kind=ProviderKind.OPENAI_COMPATIBLE,
        provider_name="Example Provider",
        quest_title="Badminton action recognition",
        selected_ideas=[
            {
                "idea_id": "idea_1",
                "idea_title": "Temporal consistency",
            }
        ],
        source_stage_ids={
            "demand_validation": "stage_demand",
            "experiment_planner": "stage_experiment",
            "idea_generator": "stage_idea",
            "literature_scout": "stage_lit",
        },
        stage_id="stage_paper",
    )


def test_parse_paper_writer_output_caps_confidence_and_preserves_review_sections() -> None:
    raw_content = json.dumps(
        {
            "chinese_research_brief_markdown": "# 中文研究 Brief\n\n## 已验证事实\n- 有真实场景。",
            "confidence": "high",
            "english_research_brief_markdown": (
                "# Research Brief\n\n## Verified Facts\n- Real scenario."
            ),
            "experiment_results_not_available": [],
            "human_review_required": ["Confirm data access."],
            "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\n## Results\nTBD.",
            "meeting_outline_markdown": "# Group Meeting Outline\n\n1. Motivation",
            "model_generated_hypotheses": ["Temporal consistency may improve action labels."],
            "summary": "Generated four traceable draft artifacts.",
            "verified_facts": ["The demand scenario is coach feedback."],
            "warnings": [],
        }
    )

    output = parse_paper_meeting_writer_output(raw_content, build_request())

    assert output.confidence == "medium"
    assert output.summary == (
        "Generated four review-only Markdown artifacts without verified experiment results."
    )
    assert output.source_stage_ids["experiment_planner"] == "stage_experiment"
    assert output.chinese_research_brief_markdown.startswith("# 中文研究 Brief")
    assert output.english_research_brief_markdown.startswith("# Research Brief")
    assert output.meeting_outline_markdown.startswith("# Group Meeting Outline")
    assert output.ieee_paper_skeleton_markdown.startswith("# IEEE Paper Skeleton")
    assert NO_RESULTS_NOTICE in output.experiment_results_not_available
    assert HUMAN_REVIEW_NOTICE in output.human_review_required


def test_parse_paper_writer_output_fails_closed_on_invalid_json() -> None:
    output = parse_paper_meeting_writer_output("not json", build_request())

    assert output.confidence == "low"
    assert output.chinese_research_brief_markdown == ""
    assert output.verified_facts == []
    assert "not valid structured JSON" in output.summary
    assert output.experiment_results_not_available == [NO_RESULTS_NOTICE]
    assert output.human_review_required == [HUMAN_REVIEW_NOTICE]


def test_paper_writer_runner_executes_anthropic_messages_api() -> None:
    captured_payload: dict[str, object] = {}
    model_response = {
        "chinese_research_brief_markdown": "# 中文研究 Brief\n\n## 已验证事实\n- 有真实场景。",
        "confidence": "medium",
        "english_research_brief_markdown": (
            "# Research Brief\n\n## Verified Facts\n- Real scenario."
        ),
        "experiment_results_not_available": [],
        "human_review_required": ["Confirm data access."],
        "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\n## Results\nTBD.",
        "meeting_outline_markdown": "# Group Meeting Outline\n\n1. Motivation",
        "model_generated_hypotheses": ["Temporal consistency may improve action labels."],
        "summary": "Generated four traceable draft artifacts.",
        "verified_facts": ["The demand scenario is coach feedback."],
        "warnings": [],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://api.anthropic.com/v1/messages")
        assert request.headers["x-api-key"] == "sk-test"
        assert request.headers["anthropic-version"] == "2023-06-01"
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"content": [{"text": json.dumps(model_response), "type": "text"}]},
        )

    runner = OpenAICompatiblePaperMeetingWriterRunner(
        chat_client=ProviderChatClient(
            client_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler))
        )
    )
    request = build_request().model_copy(
        update={
            "base_url": "https://api.anthropic.com/v1",
            "model": "claude-test-model",
            "provider_kind": ProviderKind.ANTHROPIC,
            "provider_name": "Anthropic",
        }
    )

    output = runner.run(request)

    assert output.summary == (
        "Generated four review-only Markdown artifacts without verified experiment results."
    )
    assert NO_RESULTS_NOTICE in output.experiment_results_not_available
    assert HUMAN_REVIEW_NOTICE in output.human_review_required
    assert captured_payload["model"] == "claude-test-model"
    assert captured_payload["max_tokens"] == DEFAULT_MAX_TOKENS
    assert "temperature" not in captured_payload


def test_paper_writer_stage_runner_supports_anthropic_provider() -> None:
    runner = PaperMeetingWriterStageRunner(OpenAICompatiblePaperMeetingWriterRunner())

    assert ProviderKind.ANTHROPIC in runner.supported_provider_kinds
