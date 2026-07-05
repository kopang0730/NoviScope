from typing import Literal, TypeAlias

from noviscope.core.json_types import JsonObject

DEMAND_VALIDATOR_AGENT_ID = "demand_validator"
IDEA_GENERATOR_AGENT_ID = "idea_generator"
EXPERIMENT_PLANNER_AGENT_ID = "experiment_planner"
PAPER_MEETING_WRITER_AGENT_ID = "paper_meeting_writer"
NO_EXTERNAL_VERIFICATION_RISK = (
    "High confidence was downgraded because no external source verification ran in this MVP stage."
)
NO_EXPERIMENT_VERIFICATION_RISK = (
    "High confidence was downgraded because hypotheses have not been experimentally verified."
)

StageConfidence: TypeAlias = Literal["high", "medium", "low", "unknown"]


def normalize_stage_output_payload(agent_id: str, output_payload: JsonObject) -> JsonObject:
    if output_payload.get("confidence") != "high":
        return output_payload

    if agent_id in {
        IDEA_GENERATOR_AGENT_ID,
        EXPERIMENT_PLANNER_AGENT_ID,
        PAPER_MEETING_WRITER_AGENT_ID,
    }:
        warnings_value = output_payload.get("warnings")
        warnings = [*warnings_value] if isinstance(warnings_value, list) else []
        string_warnings = {warning for warning in warnings if isinstance(warning, str)}
        if NO_EXPERIMENT_VERIFICATION_RISK not in string_warnings:
            warnings.append(NO_EXPERIMENT_VERIFICATION_RISK)
        return {**output_payload, "confidence": "medium", "warnings": warnings}

    if agent_id != DEMAND_VALIDATOR_AGENT_ID:
        return output_payload

    risks_value = output_payload.get("risks")
    risks = [*risks_value] if isinstance(risks_value, list) else []
    string_risks = {risk for risk in risks if isinstance(risk, str)}
    if NO_EXTERNAL_VERIFICATION_RISK not in string_risks:
        risks.append(NO_EXTERNAL_VERIFICATION_RISK)

    return {**output_payload, "confidence": "medium", "risks": risks}


def stage_confidence(agent_id: str, output_payload: JsonObject) -> StageConfidence:
    confidence = normalize_stage_output_payload(agent_id, output_payload).get("confidence")
    if confidence == "high" or confidence == "medium" or confidence == "low":
        return confidence
    return "unknown"
