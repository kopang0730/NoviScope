import type { AgentAssignment, Provider, ProviderKind, StageCard } from "../api/types";
import {
  demandValidatorAgentId,
  experimentPlannerAgentId,
  ideaGeneratorAgentId,
  literatureScoutAgentId,
  paperMeetingWriterAgentId,
} from "./stages";

export type ProviderReadinessReason =
  | "agent_default_ready"
  | "auto_select_ready"
  | "assigned_provider_inactive"
  | "assigned_provider_missing"
  | "assigned_provider_unsupported"
  | "missing_provider"
  | "not_required"
  | "server_managed";

export type ProviderReadinessSource =
  | "agent_default"
  | "auto_select"
  | "not_required"
  | "server_managed";

export type ProviderReadinessStatus = "blocked" | "not_required" | "ready" | "server_managed";

export type ProviderReadiness = {
  readonly modelName: string;
  readonly providerKind: ProviderKind | null;
  readonly providerName: string;
  readonly reason: ProviderReadinessReason;
  readonly source: ProviderReadinessSource;
  readonly status: ProviderReadinessStatus;
};

const modelBackedAgentIds = new Set([
  demandValidatorAgentId,
  experimentPlannerAgentId,
  ideaGeneratorAgentId,
  paperMeetingWriterAgentId,
]);

function isSupportedModelProvider(provider: Provider) {
  return provider.kind === "openai_compatible" || provider.kind === "custom";
}

function providerReadiness(
  provider: Provider,
  source: ProviderReadinessSource,
  reason: ProviderReadinessReason,
  modelName?: string | null,
): ProviderReadiness {
  return {
    modelName: modelName || provider.default_model,
    providerKind: provider.kind,
    providerName: provider.name,
    reason,
    source,
    status: "ready",
  };
}

function blockedReadiness(
  reason: ProviderReadinessReason,
  provider?: Provider | null,
  source: ProviderReadinessSource = "agent_default",
): ProviderReadiness {
  return {
    modelName: provider?.default_model ?? "",
    providerKind: provider?.kind ?? null,
    providerName: provider?.name ?? "",
    reason,
    source,
    status: "blocked",
  };
}

export function isModelBackedStage(stage: StageCard) {
  return modelBackedAgentIds.has(stage.agent_id);
}

export function getStageProviderReadiness(
  stage: StageCard,
  providers: readonly Provider[],
  assignments: readonly AgentAssignment[],
): ProviderReadiness {
  if (stage.agent_id === literatureScoutAgentId) {
    return {
      modelName: "openalex-works",
      providerKind: "custom",
      providerName: "OpenAlex",
      reason: "server_managed",
      source: "server_managed",
      status: "server_managed",
    };
  }

  if (!isModelBackedStage(stage)) {
    return {
      modelName: "",
      providerKind: null,
      providerName: "",
      reason: "not_required",
      source: "not_required",
      status: "not_required",
    };
  }

  const assignment = assignments.find((candidate) => candidate.agent_id === stage.agent_id);
  if (assignment?.provider_id) {
    const assignedProvider = providers.find((provider) => provider.id === assignment.provider_id);
    if (!assignedProvider) {
      return blockedReadiness("assigned_provider_missing");
    }
    if (!assignedProvider.is_active) {
      return blockedReadiness("assigned_provider_inactive", assignedProvider);
    }
    if (!isSupportedModelProvider(assignedProvider)) {
      return blockedReadiness("assigned_provider_unsupported", assignedProvider);
    }
    return providerReadiness(
      assignedProvider,
      "agent_default",
      "agent_default_ready",
      assignment.model_name,
    );
  }

  const autoSelectedProvider = providers.find(
    (provider) => provider.is_active && isSupportedModelProvider(provider),
  );
  if (autoSelectedProvider) {
    return providerReadiness(autoSelectedProvider, "auto_select", "auto_select_ready");
  }

  return blockedReadiness("missing_provider", null, "auto_select");
}
