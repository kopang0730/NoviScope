from pydantic import JsonValue
from sqlmodel import Session

from noviscope.agents.paper_meeting_writer_artifacts import PAPER_ARTIFACT_POLICY_VERSION
from noviscope.core.stage_policy import CODE_RUNNER_AGENT_ID
from noviscope.db.session import create_db_engine
from noviscope.models.quest import StageCard, StageStatus


def add_trusted_code_result_stage(
    database_url: str,
    quest_id: str,
    result_record: dict[str, JsonValue] | None = None,
) -> None:
    effective_result = result_record if result_record is not None else {
        "artifact_uri": "/data/noviscope/runs/run-001/metrics.json",
        "baseline_name": "Pose-based action classifier",
        "dataset_name": "Badminton clips v1",
        "metric_name": "Action classification accuracy",
        "metric_unit": "%",
        "metric_value": 78.4,
        "result_status": "verified",
        "run_id": "run-001",
    }
    engine = create_db_engine(database_url)
    try:
        with Session(engine) as session:
            session.add(
                StageCard(
                    agent_id=CODE_RUNNER_AGENT_ID,
                    human_approved=True,
                    output_payload={"experiment_results": [effective_result]},
                    quest_id=quest_id,
                    status=StageStatus.COMPLETE,
                    title="Code runner",
                )
            )
            session.commit()
    finally:
        engine.dispose()


def set_server_paper_stage(
    database_url: str,
    stage_id: str,
    output_payload: dict[str, JsonValue],
    *,
    human_approved: bool | None,
    guardrailed: bool = True,
) -> None:
    engine = create_db_engine(database_url)
    try:
        with Session(engine) as session:
            stage = session.get(StageCard, stage_id)
            assert stage is not None
            stage.evidence_payload = (
                {"artifact_policy_version": PAPER_ARTIFACT_POLICY_VERSION}
                if guardrailed
                else {}
            )
            stage.human_approved = human_approved
            stage.output_payload = output_payload
            stage.status = StageStatus.COMPLETE
            stage.summary = "Server-generated review-only writing artifacts."
            session.add(stage)
            session.commit()
    finally:
        engine.dispose()
