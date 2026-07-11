from pydantic import SecretStr

from noviscope.agents.paper_meeting_writer import (
    PaperMeetingWriterRequest,
)
from noviscope.models.provider import ProviderKind


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
                    "source_agent_id": "code_runner",
                },
                {
                    "artifact_uri": ("/data/noviscope/runs/run-20260707-unchecked/metrics.json"),
                    "baseline_name": "Pose-based action classifier",
                    "dataset_name": "Badminton training clips v1",
                    "metric_name": "Frame-level temporal consistency",
                    "metric_unit": "",
                    "metric_value": 0.91,
                    "provenance_note": ("Metric exists but has not been independently checked."),
                    "result_status": "needs_review",
                    "review_notes": "Needs independent review.",
                    "run_id": "run-20260707-unchecked",
                },
            ],
            "summary": "Experiment plan with recorded result artifacts.",
        },
        initial_direction="Badminton action recognition",
        model="example-chat",
        papers=[
            {
                "paper_ref": "https://openalex.org/W123",
                "title": "Badminton benchmark",
            }
        ],
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


def untrusted_verified_result_request() -> PaperMeetingWriterRequest:
    request = build_request_with_experiment_results()
    experiment_plan = dict(request.experiment_plan)
    experiment_plan["experiment_results"] = [
        {
            "artifact_uri": "/tmp/manual-metric.json",
            "baseline_name": "Manually patched baseline",
            "dataset_name": "Badminton training clips v1",
            "metric_name": "Action classification accuracy",
            "metric_unit": "%",
            "metric_value": 99.0,
            "provenance_note": "Manually patched into the planner payload.",
            "result_status": "verified",
            "review_notes": "Looks good.",
            "run_id": "manual-run",
        }
    ]
    return request.model_copy(update={"experiment_plan": experiment_plan})


def request_with_trusted_result() -> PaperMeetingWriterRequest:
    request = build_request_with_experiment_results()
    experiment_plan = dict(request.experiment_plan)
    records = list(experiment_plan["experiment_results"])
    experiment_plan["experiment_results"] = records[1:]
    return request.model_copy(
        update={
            "experiment_plan": experiment_plan,
            "verified_experiment_results": [records[0]],
        }
    )


def request_with_late_verified_result() -> PaperMeetingWriterRequest:
    request = build_request_with_experiment_results()
    review_records = []
    for index in range(11):
        review_records.append(
            {
                "artifact_uri": f"/data/noviscope/runs/review-{index}/metrics.json",
                "baseline_name": "Pose-based action classifier",
                "dataset_name": "Badminton training clips v1",
                "metric_name": "Review-only metric",
                "metric_unit": "%",
                "metric_value": 50.0 + index,
                "provenance_note": ("Metric exists but has not been independently checked."),
                "result_status": "needs_review",
                "review_notes": "Needs independent review.",
                "run_id": f"review-run-{index}",
            }
        )
    verified_record = {
        "artifact_uri": "/data/noviscope/runs/late-verified/metrics.json",
        "baseline_name": "Pose-based action classifier",
        "dataset_name": "Badminton training clips v1",
        "metric_name": "Late verified accuracy",
        "metric_unit": "%",
        "metric_value": 82.5,
        "provenance_note": "Recorded by the code runner from local run logs.",
        "result_status": "verified",
        "review_notes": "Evidence auditor matched the metric file to the run id.",
        "run_id": "late-verified-run",
        "source_agent_id": "evidence_auditor",
    }
    experiment_plan = dict(request.experiment_plan)
    experiment_plan["experiment_results"] = [*review_records, verified_record]
    return request.model_copy(update={"experiment_plan": experiment_plan})


def request_with_late_trusted_result() -> PaperMeetingWriterRequest:
    request = request_with_late_verified_result()
    experiment_plan = dict(request.experiment_plan)
    records = list(experiment_plan["experiment_results"])
    experiment_plan["experiment_results"] = records[:-1]
    return request.model_copy(
        update={
            "experiment_plan": experiment_plan,
            "verified_experiment_results": [records[-1]],
        }
    )
