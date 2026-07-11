import type { UpdateAgentAssignmentPayload } from "../api/agent-assignments";
import type {
  AgentAssignment,
  AutomationStatus,
  Provider,
  ProviderRequirement,
  WorkflowAgentCapability,
} from "../api/types";

export type ProviderScopeTab = "shared" | "personal";

export type AgentAssignmentDraft = {
  readonly modelName: string;
  readonly providerId: string;
};

export type AgentAssignmentRow = {
  readonly agentId: string;
  readonly displayName: string;
  readonly editable: boolean;
  readonly effectiveModel: string | null;
  readonly modelName: string;
  readonly providerId: string;
  readonly providerIsActive: boolean | null;
  readonly providerName: string | null;
  readonly providerRequirement: ProviderRequirement;
  readonly status: AutomationStatus;
  readonly statusDetail: string;
};

export type AgentAssignmentUpdate = {
  readonly agentId: string;
  readonly payload: UpdateAgentAssignmentPayload;
};

function assignmentForAgent(
  assignments: readonly AgentAssignment[],
  agentId: string,
): AgentAssignment | null {
  return assignments.find((assignment) => assignment.agent_id === agentId) ?? null;
}

function providerRequirementForCapability(
  capability: WorkflowAgentCapability,
): ProviderRequirement {
  return capability.automation_status === "planned"
    ? "not_implemented"
    : capability.provider_requirement;
}

export function filterProviders(
  providers: readonly Provider[],
  scope: ProviderScopeTab,
): readonly Provider[] {
  return providers.filter((provider) => provider.scope === scope);
}

export function buildAssignmentRows(
  assignments: readonly AgentAssignment[],
  capabilities: readonly WorkflowAgentCapability[],
): readonly AgentAssignmentRow[] {
  return capabilities.map((capability) => {
    const assignment = assignmentForAgent(assignments, capability.agent_id);
    const providerRequirement = providerRequirementForCapability(capability);

    return {
      agentId: capability.agent_id,
      displayName: capability.display_name,
      editable:
        capability.automation_status === "implemented" &&
        capability.stage_runner_available &&
        providerRequirement === "model_provider",
      effectiveModel: assignment?.effective_model ?? null,
      modelName: assignment?.model_name ?? "",
      providerId: assignment?.provider_id ?? "",
      providerIsActive: assignment?.provider_is_active ?? null,
      providerName: assignment?.provider_name ?? null,
      providerRequirement,
      status: capability.automation_status,
      statusDetail: capability.status_detail,
    };
  });
}

function normalizedDraft(draft: AgentAssignmentDraft): AgentAssignmentDraft {
  const providerId = draft.providerId.trim();
  return {
    modelName: providerId ? draft.modelName.trim() : "",
    providerId,
  };
}

export function isAssignmentRowDirty(
  row: AgentAssignmentRow,
  draft: AgentAssignmentDraft,
): boolean {
  if (!row.editable) {
    return false;
  }

  const normalizedCurrent = normalizedDraft({
    modelName: row.modelName,
    providerId: row.providerId,
  });
  const normalizedNext = normalizedDraft(draft);
  return (
    normalizedCurrent.providerId !== normalizedNext.providerId ||
    normalizedCurrent.modelName !== normalizedNext.modelName
  );
}

export function buildAssignmentUpdates(
  rows: readonly AgentAssignmentRow[],
  drafts: Readonly<Record<string, AgentAssignmentDraft>>,
): readonly AgentAssignmentUpdate[] {
  const updates: AgentAssignmentUpdate[] = [];

  for (const row of rows) {
    const draft = drafts[row.agentId];
    if (!draft || !isAssignmentRowDirty(row, draft)) {
      continue;
    }

    const normalized = normalizedDraft(draft);
    updates.push({
      agentId: row.agentId,
      payload: {
        model_name: normalized.modelName || null,
        provider_id: normalized.providerId || null,
      },
    });
  }

  return updates;
}
