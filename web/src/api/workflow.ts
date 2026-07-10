import { apiRequest } from "./client";
import type {
  WorkflowCapabilitiesResponse,
  WorkflowCanvasTemplate,
  WorkflowNextActionsResponse,
} from "./types";

export async function getWorkflowCapabilities() {
  const response = await apiRequest<WorkflowCapabilitiesResponse>("/api/workflow/capabilities");
  return response.agents;
}

export function getWorkflowCanvasTemplate() {
  return apiRequest<WorkflowCanvasTemplate>("/api/workflow/canvas-template");
}

export function getWorkflowNextActions(questId: string) {
  return apiRequest<WorkflowNextActionsResponse>(`/api/quests/${questId}/workflow-next-actions`);
}
