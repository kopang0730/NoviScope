import json

import pytest
from paper_meeting_writer_model_outputs import model_output_without_result_guardrails
from paper_meeting_writer_result_helpers import (
    build_request_with_experiment_results,
    request_with_trusted_result,
)

from noviscope.agents.paper_meeting_writer import parse_paper_meeting_writer_output


def test_unknown_planner_result_status_remains_review_visible() -> None:
    request = build_request_with_experiment_results()
    experiment_plan = dict(request.experiment_plan)
    record = dict(experiment_plan["experiment_results"][0])
    record.pop("result_status")
    experiment_plan["experiment_results"] = [record]

    output = parse_paper_meeting_writer_output(
        model_output_without_result_guardrails(),
        request.model_copy(update={"experiment_plan": experiment_plan}),
    )

    assert any("run-20260707-baseline" in item for item in output.human_review_required)


def test_trusted_results_clear_all_stale_no_result_notices() -> None:
    raw_output = json.loads(model_output_without_result_guardrails())
    raw_output["experiment_results_not_available"] = [
        "No verified results are available in this draft."
    ]

    output = parse_paper_meeting_writer_output(
        json.dumps(raw_output),
        request_with_trusted_result(),
    )

    assert output.experiment_results_not_available == []


@pytest.mark.parametrize(
    "field",
    ["artifact_uri", "baseline_name", "dataset_name", "metric_name", "run_id"],
)
def test_blank_trusted_result_identity_requires_review(field: str) -> None:
    request = request_with_trusted_result()
    record = dict(request.verified_experiment_results[0])
    record[field] = "   "

    output = parse_paper_meeting_writer_output(
        model_output_without_result_guardrails(),
        request.model_copy(update={"verified_experiment_results": [record]}),
    )

    assert output.verified_facts == []
    assert output.human_review_required


def test_dimensionless_trusted_metric_allows_an_empty_unit() -> None:
    request = request_with_trusted_result()
    record = dict(request.verified_experiment_results[0])
    record["metric_unit"] = ""

    output = parse_paper_meeting_writer_output(
        model_output_without_result_guardrails(),
        request.model_copy(update={"verified_experiment_results": [record]}),
    )

    assert len(output.verified_facts) == 1
    assert "= 78.4 on Badminton training clips v1" in output.verified_facts[0]
