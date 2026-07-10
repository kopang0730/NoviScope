import type { WorkflowAgentCapability, WorkflowNextAction } from "../api/types";

export function supportsWorkflowProviderOverride(
  action: WorkflowNextAction,
  capabilities: readonly WorkflowAgentCapability[],
) {
  const capability = capabilities.find((item) => item.agent_id === action.agent_id);
  return (
    action.action_type === "run_stage" &&
    capability?.stage_runner_available === true &&
    capability.provider_requirement === "model_provider"
  );
}
