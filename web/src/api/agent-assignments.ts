import { apiRequest } from "./client";
import type { AgentAssignment } from "./types";

type AgentAssignmentsResponse = {
  assignments: AgentAssignment[];
};

export type UpdateAgentAssignmentPayload = {
  provider_id: string | null;
  model_name?: string | null;
};

export async function getAgentAssignments() {
  const response = await apiRequest<AgentAssignmentsResponse>("/api/agent-assignments");
  return response.assignments;
}

export function updateAgentAssignment(agentId: string, payload: UpdateAgentAssignmentPayload) {
  return apiRequest<AgentAssignment>(`/api/agent-assignments/${agentId}`, {
    body: payload,
    method: "PUT",
  });
}
