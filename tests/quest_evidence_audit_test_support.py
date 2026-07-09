from pydantic import JsonValue
from sqlmodel import Session

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
                    agent_id="code_runner",
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
