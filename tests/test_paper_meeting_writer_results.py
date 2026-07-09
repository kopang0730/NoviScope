import json

from paper_meeting_writer_model_outputs import (
    model_output_with_hallucinated_verified_result,
    model_output_without_result_guardrails,
)
from paper_meeting_writer_result_helpers import (
    build_request_with_experiment_results,
    request_with_late_trusted_result,
    request_with_late_verified_result,
    request_with_trusted_result,
    untrusted_verified_result_request,
)
from pydantic import SecretStr

from noviscope.agents.paper_meeting_writer import (
    HUMAN_REVIEW_NOTICE,
    NO_RESULTS_NOTICE,
    PaperMeetingWriterOutput,
    PaperMeetingWriterRequest,
    PaperMeetingWriterStageRunner,
    parse_paper_meeting_writer_output,
)
from noviscope.agents.paper_meeting_writer_prompt import build_chat_completion_payload
from noviscope.agents.paper_meeting_writer_results import NEEDS_REVIEW_WARNING
from noviscope.agents.stage_runner import ModelProviderCredentials, StageRunContext
from noviscope.models.provider import ProviderKind
from noviscope.models.quest import Quest, StageCard, StageStatus


def test_parse_writer_output_preserves_only_verified_experiment_results() -> None:
    output = parse_paper_meeting_writer_output(
        model_output_without_result_guardrails(),
        request_with_trusted_result(),
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


def test_parse_writer_output_rejects_hallucinated_verified_result_facts() -> None:
    output = parse_paper_meeting_writer_output(
        model_output_with_hallucinated_verified_result(),
        build_request_with_experiment_results().model_copy(
            update={"experiment_plan": {"summary": "Plan only."}}
        ),
    )

    assert output.verified_facts == []
    assert NO_RESULTS_NOTICE in output.experiment_results_not_available
    assert not any(
        fact.startswith("Verified experiment result:") for fact in output.verified_facts
    )


def test_planner_patched_verified_result_requires_trusted_source_agent() -> None:
    output = parse_paper_meeting_writer_output(
        model_output_without_result_guardrails(),
        untrusted_verified_result_request(),
    )

    assert NO_RESULTS_NOTICE in output.experiment_results_not_available
    assert not any(
        fact.startswith("Verified experiment result:") for fact in output.verified_facts
    )
    assert any("manual-run" in item for item in output.human_review_required)
    assert NEEDS_REVIEW_WARNING in output.warnings


def test_prompt_payload_separates_verified_and_review_needed_results() -> None:
    payload = build_chat_completion_payload(request_with_trusted_result())
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
    assert "experiment_results" not in user_payload["experiment_plan"]
    user_content = payload["messages"][1]["content"]
    assert "0.91" not in user_content
    assert "run-20260707-unchecked/metrics.json" not in user_content


def test_prompt_context_keeps_verified_results_after_ten_review_records() -> None:
    payload = build_chat_completion_payload(request_with_late_trusted_result())
    result_context = json.loads(payload["messages"][1]["content"])[
        "experiment_result_context"
    ]

    assert result_context["verified_result_count"] == 1
    assert result_context["needs_review_result_count"] == 11
    assert result_context["verified_result_facts"] == [
        "Verified experiment result: Late verified accuracy = 82.5% "
        "on Badminton training clips v1 using Pose-based action classifier "
        "(run late-verified-run; artifact /data/noviscope/runs/late-verified/metrics.json)."
    ]


def test_stage_runner_passes_untruncated_experiment_results_to_writer() -> None:
    captured_request: PaperMeetingWriterRequest | None = None

    class CapturingPaperRunner:
        def run(self, request: PaperMeetingWriterRequest) -> PaperMeetingWriterOutput:
            nonlocal captured_request
            captured_request = request
            return PaperMeetingWriterOutput(
                chinese_research_brief_markdown="# 中文研究 Brief",
                confidence="medium",
                english_research_brief_markdown="# Research Brief",
                experiment_results_not_available=[NO_RESULTS_NOTICE],
                human_review_required=[HUMAN_REVIEW_NOTICE],
                ieee_paper_skeleton_markdown="# IEEE Paper Skeleton",
                meeting_outline_markdown="# Group Meeting Outline",
                model_generated_hypotheses=[],
                raw_response="{}",
                source_stage_ids=request.source_stage_ids,
                summary="Generated draft artifacts.",
                verified_facts=[],
                warnings=[],
            )

    request = request_with_late_verified_result()
    experiment_stage = StageCard(
        agent_id="experiment_planner",
        human_approved=True,
        output_payload=request.experiment_plan,
        quest_id="quest_1",
        status=StageStatus.COMPLETE,
        title="Experiment planner",
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
        workflow_stages=(experiment_stage,),
    )

    PaperMeetingWriterStageRunner(CapturingPaperRunner()).run(context)

    assert captured_request is not None
    assert len(captured_request.experiment_plan["experiment_results"]) == 12
    assert (
        captured_request.experiment_plan["experiment_results"][11]["run_id"]
        == "late-verified-run"
    )
