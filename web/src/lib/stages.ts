import type { StageCard } from "../api/types";

export const demandValidatorAgentId = "demand_validator";

export type StageRunAvailability = {
  readonly canRun: boolean;
  readonly reason: string;
};

export function canRunDemandValidationStage(stage: StageCard) {
  return (
    stage.agent_id === demandValidatorAgentId &&
    (stage.status === "pending" || stage.status === "blocked")
  );
}

function readPayloadString(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

export function getStageRunAvailability(stage: StageCard): StageRunAvailability {
  if (canRunDemandValidationStage(stage)) {
    return {
      canRun: true,
      reason: "Ready if an active OpenAI-compatible or custom provider is configured.",
    };
  }

  if (stage.status === "blocked") {
    const detail = readPayloadString(stage.evidence_payload, "blocking_detail");
    return {
      canRun: false,
      reason: detail || "This stage is blocked. Open the stage to review the reason.",
    };
  }

  if (stage.status === "complete") {
    return {
      canRun: false,
      reason: "Completed. Review the output and human approval before continuing.",
    };
  }

  if (stage.status === "running") {
    return {
      canRun: false,
      reason: "Already running.",
    };
  }

  return {
    canRun: false,
    reason: "No runner has been implemented for this workflow stage yet.",
  };
}
