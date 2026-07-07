import type { StageCard } from "../api/types";
import type { TranslationKey } from "../i18n/i18n-context";
import { labelFromEnum } from "./format";
import type { ProviderReadinessData } from "./provider-readiness-data";
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

function firstDetailValue(items: readonly string[], fallback: string) {
  return items[0] ?? fallback;
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
    const fallback = t("notAvailable");
    details.push({
      label: t("verifiedFacts"),
      value: firstDetailValue(readStringArray(stage.output_payload, "verified_facts"), fallback),
    });
    details.push({
      label: t("modelGeneratedHypotheses"),
      value: firstDetailValue(
        readStringArray(stage.output_payload, "model_generated_hypotheses"),
        fallback,
      ),
    });
    details.push({
      label: t("experimentResultsNotAvailable"),
      value: firstDetailValue(
        readStringArray(stage.output_payload, "experiment_results_not_available"),
        fallback,
      ),
    });
    details.push({
      label: t("humanReviewRequired"),
      value: firstDetailValue(readStringArray(stage.output_payload, "human_review_required"), fallback),
    });
  }

  if (blockingDetail) {
    details.push({ label: t("canvasBlocked"), value: blockingDetail });
  }

  return details.slice(0, 4);
}
