import type { TranslationKey } from "../i18n/i18n-context";
import type {
  ProviderReadinessReason,
  ProviderReadinessSource,
  ProviderReadinessStatus,
} from "./provider-readiness";

export function providerReadinessLabelKey(status: ProviderReadinessStatus): TranslationKey {
  if (status === "blocked") {
    return "providerReadinessBlocked";
  }
  if (status === "server_managed") {
    return "providerReadinessServerManaged";
  }
  if (status === "ready") {
    return "providerReadinessReady";
  }
  return "providerReadinessNotRequired";
}

export function providerReadinessReasonKey(reason: ProviderReadinessReason): TranslationKey {
  const reasonKeys: Record<ProviderReadinessReason, TranslationKey> = {
    agent_default_ready: "providerReadinessReasonAgentDefaultReady",
    assigned_provider_inactive: "providerReadinessReasonAssignedInactive",
    assigned_provider_missing: "providerReadinessReasonAssignedMissing",
    assigned_provider_unsupported: "providerReadinessReasonAssignedUnsupported",
    auto_select_ready: "providerReadinessReasonAutoSelectReady",
    missing_provider: "providerReadinessReasonMissingProvider",
    not_required: "providerReadinessReasonNotRequired",
    server_managed: "providerReadinessReasonServerManaged",
  };
  return reasonKeys[reason];
}

export function providerReadinessSourceKey(source: ProviderReadinessSource): TranslationKey {
  const sourceKeys: Record<ProviderReadinessSource, TranslationKey> = {
    agent_default: "providerReadinessSourceAgentDefault",
    auto_select: "providerReadinessSourceAutoSelect",
    not_required: "providerReadinessSourceNotRequired",
    server_managed: "providerReadinessSourceServerManaged",
  };
  return sourceKeys[source];
}
