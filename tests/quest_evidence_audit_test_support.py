from pydantic import JsonValue
from sqlmodel import Session, select

from noviscope.agents.paper_meeting_writer_artifacts import PAPER_ARTIFACT_POLICY_VERSION
from noviscope.api.evidence_audit_contract import EVIDENCE_AUDIT_POLICY_VERSION
from noviscope.api.evidence_audit_snapshot import (
    EVIDENCE_AUDIT_FINGERPRINT_KEY,
    evidence_audit_stage_fingerprint,
)
from noviscope.core.stage_policy import CODE_RUNNER_AGENT_ID, EVIDENCE_AUDITOR_AGENT_ID
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


def add_approved_evidence_auditor_stage(
    database_url: str,
    quest_id: str,
    *,
    alignment_value: JsonValue = True,
    valid_contract: bool = True,
) -> None:
    evidence_payload: dict[str, JsonValue] = {}
    if valid_contract:
        evidence_payload = {
            "audit_artifact_uri": "/data/noviscope/audits/quest-audit.json",
            "audit_policy_version": EVIDENCE_AUDIT_POLICY_VERSION,
            "claim_reference_alignment": alignment_value,
            "experiment_claim_alignment": alignment_value,
        }
    engine = create_db_engine(database_url)
    try:
        with Session(engine) as session:
            stages = list(
                session.exec(select(StageCard).where(StageCard.quest_id == quest_id)).all()
            )
            if valid_contract:
                evidence_payload[EVIDENCE_AUDIT_FINGERPRINT_KEY] = (
                    evidence_audit_stage_fingerprint(stages)
                )
            session.add(
                StageCard(
                    agent_id=EVIDENCE_AUDITOR_AGENT_ID,
                    evidence_payload=evidence_payload,
                    human_approved=True,
                    output_payload={},
                    quest_id=quest_id,
                    status=StageStatus.COMPLETE,
                    title="Evidence auditor",
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
