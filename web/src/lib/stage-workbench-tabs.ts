import type { StageCard } from "../api/types";
import type { TranslationKey } from "../i18n/i18n-context";
import {
  hasStageEvidence,
  isHumanGateStage,
  isImplementedStageRole,
  isOutputCapableStage,
} from "./research-canvas-data";

export type StageWorkbenchTabId = "overview" | "evidence" | "run" | "review" | "artifacts";

type TabDefinition = {
  readonly id: StageWorkbenchTabId;
  readonly labelKey: TranslationKey;
};

export const stageWorkbenchTabs: readonly TabDefinition[] = [
  { id: "overview", labelKey: "stageWorkbenchOverview" },
  { id: "evidence", labelKey: "stageWorkbenchEvidence" },
  { id: "run", labelKey: "stageWorkbenchRun" },
  { id: "review", labelKey: "stageWorkbenchReview" },
  { id: "artifacts", labelKey: "stageWorkbenchArtifacts" },
];

export function isStageWorkbenchTabAvailable(tabId: StageWorkbenchTabId, stage: StageCard) {
  switch (tabId) {
    case "overview":
      return true;
    case "evidence":
      return isImplementedStageRole(stage) || hasStageEvidence(stage);
    case "run":
      return isImplementedStageRole(stage);
    case "review":
      return isHumanGateStage(stage);
    case "artifacts":
      return isOutputCapableStage(stage);
  }
}
