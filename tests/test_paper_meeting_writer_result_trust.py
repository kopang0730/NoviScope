import json

import pytest
from paper_meeting_writer_model_outputs import model_output_without_result_guardrails
from paper_meeting_writer_result_helpers import build_request_with_experiment_results
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
from noviscope.agents.stage_runner import ModelProviderCredentials, StageRunContext
from noviscope.core.json_types import JsonObject
from noviscope.models.provider import ProviderKind
from noviscope.models.quest import Quest, StageCard, StageStatus


def result_record(run_id: str, metric_value: int | float = 78.4) -> JsonObject:
    return {
        "artifact_uri": f"/data/noviscope/runs/{run_id}/metrics.json",
        "baseline_name": "Pose-based action classifier",
        "dataset_name": "Badminton training clips v1",
        "metric_name": "Action classification accuracy",
        "metric_unit": "%",
        "metric_value": metric_value,
        "result_status": "verified",
        "run_id": run_id,
    }


def test_planner_result_cannot_self_assert_trusted_agent() -> None:
    request = build_request_with_experiment_results()

    output = parse_paper_meeting_writer_output(
        model_output_without_result_guardrails(),
        request,
    )

    assert NO_RESULTS_NOTICE in output.experiment_results_not_available
    assert not any(fact.startswith("Verified experiment result:") for fact in output.verified_facts)
    assert any("run-20260707-baseline" in item for item in output.human_review_required)


def test_stage_runner_uses_only_approved_code_runner_metric_records() -> None:
    captured_request: PaperMeetingWriterRequest | None = None
    approved_record = result_record("approved-code-run")
    auditor_record = result_record("auditor-owned-run")

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

    experiment_stage = StageCard(
        agent_id="experiment_planner",
        human_approved=True,
        output_payload={"summary": "Plan only."},
        quest_id="quest_1",
        status=StageStatus.COMPLETE,
        title="Experiment planner",
    )
    approved_code_stage = StageCard(
        agent_id="code_runner",
        human_approved=True,
        output_payload={"metric_records": [approved_record]},
        quest_id="quest_1",
        status=StageStatus.COMPLETE,
        title="Code runner",
    )
    approved_audit_stage = StageCard(
        agent_id="evidence_auditor",
        human_approved=True,
        output_payload={"experiment_results": [auditor_record]},
        quest_id="quest_1",
        status=StageStatus.COMPLETE,
        title="Evidence auditor",
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
        workflow_stages=(
            experiment_stage,
            approved_code_stage,
            approved_audit_stage,
        ),
    )

    PaperMeetingWriterStageRunner(CapturingPaperRunner()).run(context)

    assert captured_request is not None
    assert getattr(captured_request, "verified_experiment_results", None) == [approved_record]
    assert captured_request.source_stage_ids.get("demand_validation") == ""
    assert captured_request.source_stage_ids.get("code_runner") == approved_code_stage.id
    assert "demand_validator" not in captured_request.source_stage_ids


def test_prompt_result_context_caps_samples_but_counts_all_records() -> None:
    request = build_request_with_experiment_results()
    review_records = [
        {**result_record(f"review-{index}"), "result_status": "needs_review"} for index in range(12)
    ]
    verified_records = [result_record(f"verified-{index}") for index in range(12)]
    bounded_request = request.model_copy(
        update={
            "experiment_plan": {"experiment_results": review_records},
            "verified_experiment_results": verified_records,
        }
    )

    payload = build_chat_completion_payload(bounded_request)
    result_context = json.loads(payload["messages"][1]["content"])["experiment_result_context"]

    assert result_context["verified_result_count"] == 12
    assert result_context["needs_review_result_count"] == 12
    assert len(result_context["verified_result_facts"]) == 10
    assert len(result_context["results_requiring_review"]) == 10


def test_trusted_result_fact_preserves_exact_integer_metric() -> None:
    exact_value = 9_007_199_254_740_993
    request = build_request_with_experiment_results().model_copy(
        update={
            "experiment_plan": {"summary": "Plan only."},
            "verified_experiment_results": [result_record("exact-run", exact_value)],
        }
    )

    output = parse_paper_meeting_writer_output(
        model_output_without_result_guardrails(),
        request,
    )

    assert any(
        f"Action classification accuracy = {exact_value}%" in fact for fact in output.verified_facts
    )


@pytest.mark.parametrize("metric_value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_metric_never_becomes_verified_fact(metric_value: float) -> None:
    request = build_request_with_experiment_results().model_copy(
        update={
            "experiment_plan": {"summary": "Plan only."},
            "verified_experiment_results": [result_record("invalid-run", metric_value)],
        }
    )

    output = parse_paper_meeting_writer_output(
        model_output_without_result_guardrails(),
        request,
    )

    assert output.verified_facts == []
    assert NO_RESULTS_NOTICE in output.experiment_results_not_available
    assert any("invalid-run" in item for item in output.human_review_required)
