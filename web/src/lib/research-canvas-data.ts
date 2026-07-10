import type { StageCard } from "../api/types";
import type { TranslationKey } from "../i18n/i18n-context";
import { labelFromEnum } from "./format";
import type { ProviderReadinessData } from "./provider-readiness-data";
import type { MacroPhaseId, MacroPhaseView } from "./research-workbench";
import { readSourceStageIds } from "./source-stage-ids";
import { getStageRunGate } from "./stage-run-gate";
import {
  demandValidatorAgentId,
  experimentPlannerAgentId,
  ideaGeneratorAgentId,
  literatureScoutAgentId,
  paperMeetingWriterAgentId,
} from "./stages";
import { getWorkflowStageReadiness } from "./workflow-readiness";

export type CanvasDetail = {
  readonly label: string;
  readonly value: string;
};

export type CanvasStageFlow = {
  readonly inputKey: TranslationKey;
  readonly outputKey: TranslationKey;
};

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

function readStringArray(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function readRecordArray(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return Array.isArray(value)
    ? value.filter(
        (item): item is Readonly<Record<string, unknown>> =>
          typeof item === "object" && item !== null && !Array.isArray(item),
      )
    : [];
}

function findSelectedIdeaTitle(stage: StageCard) {
  const selectedIdeaIds = new Set(readStringArray(stage.output_payload, "selected_idea_ids"));
  const ideas = readRecordArray(stage.output_payload, "ideas");
  const selectedIdea = ideas.find((idea) => selectedIdeaIds.has(readString(idea, "idea_id")));
  return selectedIdea ? readString(selectedIdea, "idea_title") : "";
}

export function isHumanGateStage(stage: StageCard) {
  return (
    stage.agent_id === demandValidatorAgentId ||
    stage.agent_id === ideaGeneratorAgentId ||
    stage.agent_id === experimentPlannerAgentId
  );
}

export function needsHumanReview(stage: StageCard) {
  return stage.status === "complete" && isHumanGateStage(stage) && stage.human_approved === null;
}

export function hasStageEvidence(stage: StageCard) {
  return (
    Object.keys(stage.evidence_payload).length > 0
    || Object.keys(readSourceStageIds(stage.output_payload)).length > 0
  );
}

export function isImplementedStageRole(stage: StageCard) {
  return (
    stage.agent_id === demandValidatorAgentId
    || stage.agent_id === literatureScoutAgentId
    || stage.agent_id === ideaGeneratorAgentId
    || stage.agent_id === experimentPlannerAgentId
    || stage.agent_id === paperMeetingWriterAgentId
  );
}

export function isOutputCapableStage(stage: StageCard) {
  return isImplementedStageRole(stage) || Object.keys(stage.output_payload).length > 0;
}

export function findNextActionStage(
  stages: readonly StageCard[],
  providerReadinessData: ProviderReadinessData,
) {
  return (
    stages.find((stage) => stage.status === "running")
    ?? stages.find(needsHumanReview)
    ?? stages.find((stage) => getStageRunGate({ providerReadinessData, stage, stages }).canRun)
    ?? stages.find((stage) => getWorkflowStageReadiness(stage, stages).canRun)
    ?? stages.find((stage) => stage.status === "blocked")
    ?? stages.find((stage) => stage.status !== "complete")
    ?? null
  );
}

export function phaseKeyForAgent(agentId: string): TranslationKey {
  if (agentId === demandValidatorAgentId) {
    return "canvasPhaseDemand";
  }
  if (agentId === literatureScoutAgentId) {
    return "canvasPhaseDiscovery";
  }
  if (agentId === ideaGeneratorAgentId) {
    return "canvasPhaseHypothesis";
  }
  if (agentId === experimentPlannerAgentId) {
    return "canvasPhaseExperiment";
  }
  if (agentId === paperMeetingWriterAgentId) {
    return "canvasPhaseWriting";
  }
  return "canvasPhaseWorkflow";
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
    return {
      flow,
      signal: t("canvasPhasePlannedSignal"),
      state: "planned",
      titleKey,
    };
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

export function flowForAgent(agentId: string): CanvasStageFlow {
  if (agentId === demandValidatorAgentId) {
    return {
      inputKey: "canvasFlowDemandInput",
      outputKey: "canvasFlowDemandOutput",
    };
  }
  if (agentId === literatureScoutAgentId) {
    return {
      inputKey: "canvasFlowDiscoveryInput",
      outputKey: "canvasFlowDiscoveryOutput",
    };
  }
  if (agentId === ideaGeneratorAgentId) {
    return {
      inputKey: "canvasFlowHypothesisInput",
      outputKey: "canvasFlowHypothesisOutput",
    };
  }
  if (agentId === experimentPlannerAgentId) {
    return {
      inputKey: "canvasFlowExperimentInput",
      outputKey: "canvasFlowExperimentOutput",
    };
  }
  if (agentId === paperMeetingWriterAgentId) {
    return {
      inputKey: "canvasFlowWritingInput",
      outputKey: "canvasFlowWritingOutput",
    };
  }
  return {
    inputKey: "canvasFlowWorkflowInput",
    outputKey: "canvasFlowWorkflowOutput",
  };
}

export function buildStageDetails(stage: StageCard, t: Translate): CanvasDetail[] {
  const details: CanvasDetail[] = [];
  const blockingDetail = readString(stage.evidence_payload, "blocking_detail");

  if (stage.agent_id === demandValidatorAgentId) {
    const scenario = readString(stage.output_payload, "real_world_scenario");
    const demandVerdict = readString(stage.evidence_payload, "human_demand_verdict");
    const demandSources = readStringArray(stage.evidence_payload, "human_demand_sources");
    if (demandVerdict) {
      details.push({ label: t("demandSourceVerdict"), value: labelFromEnum(demandVerdict) });
    }
    if (demandSources[0]) {
      details.push({ label: t("demandSourceRecordedEvidence"), value: demandSources[0] });
    }
    if (scenario) {
      details.push({ label: t("canvasEvidence"), value: scenario });
    }
  }

  if (stage.agent_id === literatureScoutAgentId) {
    const papers = readRecordArray(stage.output_payload, "papers");
    details.push({ label: t("canvasPapers"), value: String(papers.length) });
    if (papers[0]) {
      details.push({ label: t("canvasEvidence"), value: readString(papers[0], "title") });
    }
  }

  if (stage.agent_id === ideaGeneratorAgentId) {
    const selectedIdeaTitle = findSelectedIdeaTitle(stage);
    const ideas = readRecordArray(stage.output_payload, "ideas");
    details.push({ label: t("canvasIdeaCount"), value: String(ideas.length) });
    if (selectedIdeaTitle) {
      details.push({ label: t("canvasSelectedIdea"), value: selectedIdeaTitle });
    }
  }

  if (stage.agent_id === experimentPlannerAgentId) {
    const dataStatus = readString(stage.output_payload, "data_availability_status");
    const scriptPlan = readStringArray(stage.output_payload, "first_runnable_script_plan");
    const missingInputs = readStringArray(stage.evidence_payload, "missing_inputs");
    if (dataStatus) {
      details.push({ label: t("dataAvailabilityStatus"), value: labelFromEnum(dataStatus) });
    }
    if (scriptPlan.length > 0) {
      details.push({ label: t("canvasPlanSteps"), value: String(scriptPlan.length) });
    }
    if (missingInputs.length > 0) {
      details.push({ label: t("canvasInputsNeeded"), value: missingInputs.join(", ") });
    }
  }

  if (stage.agent_id === paperMeetingWriterAgentId) {
    const artifactCount = stage.evidence_payload.artifact_count;
    const downloadFormat = readString(stage.evidence_payload, "download_format");
    if (typeof artifactCount === "number") {
      details.push({ label: t("canvasArtifacts"), value: String(artifactCount) });
    }
    if (downloadFormat) {
      details.push({ label: t("canvasDownloadFormat"), value: labelFromEnum(downloadFormat) });
    }
  }

  if (blockingDetail) {
    details.push({ label: t("canvasBlocked"), value: blockingDetail });
  }

  return details.slice(0, 4);
}
