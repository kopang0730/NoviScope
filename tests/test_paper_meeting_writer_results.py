import json

from pydantic import SecretStr

from noviscope.agents.paper_meeting_writer import (
    HUMAN_REVIEW_NOTICE,
    NO_RESULTS_NOTICE,
    PaperMeetingWriterRequest,
    parse_paper_meeting_writer_output,
)
from noviscope.agents.paper_meeting_writer_output import build_stage_evidence_payload
from noviscope.agents.paper_meeting_writer_prompt import build_chat_completion_payload
from noviscope.agents.paper_meeting_writer_results import NEEDS_REVIEW_WARNING
from noviscope.agents.stage_runner import ModelProviderCredentials, StageRunContext
from noviscope.models.provider import ProviderKind
from noviscope.models.quest import Quest, StageCard


def build_request_with_experiment_results() -> PaperMeetingWriterRequest:
    return PaperMeetingWriterRequest(
        api_key=SecretStr("sk-test"),
        base_url="https://api.example.com/v1",
        demand_validation={"real_world_scenario": "Coach feedback"},
        experiment_plan={
            "experiment_results": [
                {
                    "artifact_uri": "/data/noviscope/runs/run-20260707/metrics.json",
                    "baseline_name": "Pose-based action classifier",
                    "dataset_name": "Badminton training clips v1",
                    "higher_is_better": True,
                    "metric_name": "Action classification accuracy",
                    "metric_unit": "%",
                    "metric_value": 78.4,
                    "provenance_note": "Recorded from local run log metrics.json.",
                    "result_status": "verified",
                    "review_notes": "Human checked the metric file and run id.",
                    "run_id": "run-20260707-baseline",
                },
                {
                    "artifact_uri": "/data/noviscope/runs/run-20260707-unchecked/metrics.json",
                    "baseline_name": "Pose-based action classifier",
                    "dataset_name": "Badminton training clips v1",
                    "metric_name": "Frame-level temporal consistency",
                    "metric_unit": "",
                    "metric_value": 0.91,
                    "provenance_note": "Metric exists but has not been independently checked.",
                    "result_status": "needs_review",
                    "review_notes": "Needs independent review.",
                    "run_id": "run-20260707-unchecked",
                },
            ],
            "summary": "Experiment plan with recorded result artifacts.",
        },
        initial_direction="Badminton action recognition",
        model="example-chat",
        papers=[{"paper_ref": "https://openalex.org/W123", "title": "Badminton benchmark"}],
        provider_id="provider_1",
        provider_kind=ProviderKind.OPENAI_COMPATIBLE,
        provider_name="Example Provider",
        quest_title="Badminton action recognition",
        selected_ideas=[{"idea_id": "idea_1", "idea_title": "Temporal consistency"}],
        source_stage_ids={
            "demand_validation": "stage_demand",
            "experiment_planner": "stage_experiment",
            "idea_generator": "stage_idea",
            "literature_scout": "stage_lit",
        },
        stage_id="stage_paper",
    )


def model_output_without_result_guardrails() -> str:
    return json.dumps(
        {
            "chinese_research_brief_markdown": "# 中文研究 Brief\n\n## 实验结果\n- 待整理。",
            "confidence": "high",
            "english_research_brief_markdown": "# Research Brief\n\n## Results\n- TBD.",
            "experiment_results_not_available": [NO_RESULTS_NOTICE],
            "human_review_required": [],
            "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\n## Results\nTBD.",
            "meeting_outline_markdown": "# Group Meeting Outline\n\n1. Motivation",
            "model_generated_hypotheses": ["Temporal consistency may improve action labels."],
            "summary": "Generated draft artifacts.",
            "verified_facts": [],
            "warnings": [],
        }
    )


def test_parse_writer_output_preserves_only_verified_experiment_results() -> None:
    output = parse_paper_meeting_writer_output(
        model_output_without_result_guardrails(),
        build_request_with_experiment_results(),
    )

    assert output.confidence == "medium"
    assert NO_RESULTS_NOTICE not in output.experiment_results_not_available
    assert (
        "Verified experiment result: Action classification accuracy = 78.4% "
        "on Badminton training clips v1 using Pose-based action classifier "
        "(run run-20260707-baseline; artifact "
        "/data/noviscope/runs/run-20260707/metrics.json)."
    ) in output.verified_facts
    assert any(
        "run-20260707-unchecked" in review_item
        and "Frame-level temporal consistency" in review_item
        for review_item in output.human_review_required
    )
    assert HUMAN_REVIEW_NOTICE in output.human_review_required
    assert NEEDS_REVIEW_WARNING in output.warnings


def test_prompt_payload_separates_verified_and_review_needed_results() -> None:
    payload = build_chat_completion_payload(build_request_with_experiment_results())
    system_message = payload["messages"][0]["content"]
    user_payload = json.loads(payload["messages"][1]["content"])
    result_context = user_payload["experiment_result_context"]

    assert "cite only those facts as completed results" in system_message
    assert result_context["verified_result_count"] == 1
    assert result_context["needs_review_result_count"] == 1
    assert result_context["verified_result_facts"] == [
        "Verified experiment result: Action classification accuracy = 78.4% "
        "on Badminton training clips v1 using Pose-based action classifier "
        "(run run-20260707-baseline; artifact "
        "/data/noviscope/runs/run-20260707/metrics.json)."
    ]
    assert "run-20260707-unchecked" in result_context["results_requiring_review"][0]


def test_stage_evidence_marks_verified_results_without_trusting_review_needed_results() -> None:
    output = parse_paper_meeting_writer_output(
        model_output_without_result_guardrails(),
        build_request_with_experiment_results(),
    )
    context = StageRunContext(
        provider=ModelProviderCredentials(
            api_key=SecretStr("sk-test"),
            base_url="https://api.example.com/v1",
            id="provider_1",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            model="example-chat",
            name="Example Provider",
        ),
        quest=Quest(
            initial_direction="Badminton action recognition",
            title="Badminton action recognition",
        ),
        stage=StageCard(
            agent_id="paper_meeting_writer",
            quest_id="quest_1",
            title="Paper & meeting writer",
        ),
    )

    evidence_payload = build_stage_evidence_payload(context, output)

    assert evidence_payload["no_experiment_results"] is False
    assert evidence_payload["experiment_results_require_review"] is True
