import json

from pydantic import SecretStr

from noviscope.agents.paper_meeting_writer import (
    HUMAN_REVIEW_NOTICE,
    NO_RESULTS_NOTICE,
    PaperMeetingWriterRequest,
    parse_paper_meeting_writer_output,
)
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
