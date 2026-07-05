import type { StageCard } from "../api/types";

export const demandValidatorAgentId = "demand_validator";

export function canRunDemandValidationStage(stage: StageCard) {
  return (
    stage.agent_id === demandValidatorAgentId &&
    (stage.status === "pending" || stage.status === "blocked")
  );
}
