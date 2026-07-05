import type { StageCard } from "../api/types";
import type { TranslationKey } from "../i18n/i18n-context";
import type { ProviderReadinessData } from "./provider-readiness-data";
import {
  getStageProviderReadiness,
  type ProviderReadiness,
} from "./provider-readiness";
import { providerReadinessReasonKey } from "./provider-readiness-text";
import {
  getLocalizedWorkflowReadinessReason,
  getWorkflowStageReadiness,
  type WorkflowStageReadiness,
} from "./workflow-readiness";

export type StageRunGateReason =
  | "ready"
  | "workflow_blocked"
  | "provider_loading"
  | "provider_error"
  | "provider_blocked";

export type StageRunGate = {
  readonly canRun: boolean;
  readonly providerReadiness: ProviderReadiness;
  readonly reason: StageRunGateReason;
  readonly workflowReadiness: WorkflowStageReadiness;
};

export type StageRunGateInput = {
  readonly providerReadinessData: ProviderReadinessData;
  readonly stage: StageCard;
  readonly stages: readonly StageCard[];
};

type Translate = (key: TranslationKey) => string;

function providerAllowsRun(readiness: ProviderReadiness) {
  return (
    readiness.status === "ready" ||
    readiness.status === "server_managed" ||
    readiness.status === "not_required"
  );
}

export function getStageRunGate({
  providerReadinessData,
  stage,
  stages,
}: StageRunGateInput): StageRunGate {
  const workflowReadiness = getWorkflowStageReadiness(stage, stages);
  const providerReadiness = getStageProviderReadiness(
    stage,
    providerReadinessData.providers,
    providerReadinessData.assignments,
  );

  if (!workflowReadiness.canRun) {
    return {
      canRun: false,
      providerReadiness,
      reason: "workflow_blocked",
      workflowReadiness,
    };
  }

  if (providerReadinessData.loading || !providerReadinessData.loaded) {
    return {
      canRun: false,
      providerReadiness,
      reason: "provider_loading",
      workflowReadiness,
    };
  }

  if (providerReadinessData.error) {
    return {
      canRun: false,
      providerReadiness,
      reason: "provider_error",
      workflowReadiness,
    };
  }

  if (!providerAllowsRun(providerReadiness)) {
    return {
      canRun: false,
      providerReadiness,
      reason: "provider_blocked",
      workflowReadiness,
    };
  }

  return {
    canRun: true,
    providerReadiness,
    reason: "ready",
    workflowReadiness,
  };
}

export function getLocalizedStageRunGateReason(gate: StageRunGate, t: Translate) {
  if (gate.reason === "workflow_blocked") {
    return getLocalizedWorkflowReadinessReason(gate.workflowReadiness, t);
  }
  if (gate.reason === "provider_loading") {
    return t("providerReadinessLoading");
  }
  if (gate.reason === "provider_error") {
    return t("providerReadinessLoadFailed");
  }
  if (gate.reason === "provider_blocked") {
    return t(providerReadinessReasonKey(gate.providerReadiness.reason));
  }
  return getLocalizedWorkflowReadinessReason(gate.workflowReadiness, t);
}
