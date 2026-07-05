from typing import Literal, TypeAlias

from noviscope.core.json_types import JsonObject

DEMAND_VALIDATOR_AGENT_ID = "demand_validator"
NO_EXTERNAL_VERIFICATION_RISK = (
    "High confidence was downgraded because no external source verification ran in this MVP stage."
)

StageConfidence: TypeAlias = Literal["high", "medium", "low", "unknown"]


def normalize_stage_output_payload(agent_id: str, output_payload: JsonObject) -> JsonObject:
    if agent_id != DEMAND_VALIDATOR_AGENT_ID or output_payload.get("confidence") != "high":
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
