import type { StageCard } from "../api/types";
import type { TranslationKey } from "../i18n/i18n-context";
import type { ProviderReadinessData } from "./provider-readiness-data";
import {
  flowForAgent,
  needsHumanReview,
  type CanvasStageFlow,
} from "./research-canvas-data";
import type { MacroPhaseId, MacroPhaseView } from "./research-workbench";
import { getStageRunGate } from "./stage-run-gate";

type Translate = (key: TranslationKey) => string;

export type MacroPhaseState =
  | "blocked"
  | "complete"
  | "pending"
  | "planned"
  | "review_required"
  | "runnable"
  | "running";

export type MacroPhasePresentation = {
  readonly flow: CanvasStageFlow;
  readonly signal: string;
  readonly state: MacroPhaseState;
  readonly titleKey: TranslationKey;
};

function readString(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

export function macroPhaseTitleKey(phaseId: MacroPhaseId): TranslationKey {
  switch (phaseId) {
    case "demand_scope":
      return "canvasPhaseDemandScope";
    case "literature_gap":
      return "canvasPhaseLiteratureGap";
    case "hypothesis_idea":
      return "canvasPhaseHypothesisIdea";
    case "experiment_verification":
      return "canvasPhaseExperimentVerification";
    case "paper_meeting":
      return "canvasPhasePaperMeeting";
  }
}

export function macroPhaseStateKey(state: MacroPhaseState): TranslationKey {
  switch (state) {
    case "blocked":
      return "canvasPhaseStateBlocked";
    case "complete":
      return "canvasPhaseStateComplete";
    case "pending":
      return "canvasPhaseStatePending";
    case "planned":
      return "canvasPhaseStatePlanned";
    case "review_required":
      return "canvasPhaseStateReviewRequired";
    case "runnable":
      return "canvasPhaseStateRunnable";
    case "running":
      return "canvasPhaseStateRunning";
  }
}

export function buildMacroPhasePresentation(
  phase: MacroPhaseView,
  providerReadinessData: ProviderReadinessData,
  stages: readonly StageCard[],
  t: Translate,
): MacroPhasePresentation {
  const stage = phase.primaryStage;
  const flow = flowForAgent(phase.definition.primaryAgentId);
  const titleKey = macroPhaseTitleKey(phase.definition.id);

  if (!stage) {
    return { flow, signal: t("canvasPhasePlannedSignal"), state: "planned", titleKey };
  }

  if (stage.status === "running") {
    return {
      flow,
      signal: stage.summary || t("workflowReadinessStatusRunning"),
      state: "running",
      titleKey,
    };
  }

  if (needsHumanReview(stage)) {
    return {
      flow,
      signal: stage.summary || t("humanReviewRequired"),
      state: "review_required",
      titleKey,
    };
  }

  if (stage.status === "complete") {
    return {
      flow,
      signal: stage.summary || t("canvasOutputReady"),
      state: "complete",
      titleKey,
    };
  }

  const runGate = getStageRunGate({ providerReadinessData, stage, stages });
  if (runGate.canRun) {
    return {
      flow,
      signal: stage.summary || t("canvasReadyToRun"),
      state: "runnable",
      titleKey,
    };
  }

  if (stage.status === "blocked") {
    const blockingDetail = readString(stage.evidence_payload, "blocking_detail");
    return {
      flow,
      signal: blockingDetail || t("canvasWaitingForOutput"),
      state: "blocked",
      titleKey,
    };
  }

  return {
    flow,
    signal: stage.summary || t("canvasWaitingForOutput"),
    state: "pending",
    titleKey,
  };
}
