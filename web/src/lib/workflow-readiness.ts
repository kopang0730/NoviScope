import type { StageCard } from "../api/types";
import type { TranslationKey } from "../i18n/i18n-context";
import {
  demandValidatorAgentId,
  experimentPlannerAgentId,
  ideaGeneratorAgentId,
  literatureScoutAgentId,
  paperMeetingWriterAgentId,
} from "./stages";

export type WorkflowReadinessReason =
  | "ready"
  | "status_complete"
  | "status_running"
  | "runner_not_implemented"
  | "demand_validation_required"
  | "demand_review_required"
  | "demand_evidence_review_required"
  | "gap_prerequisites_required"
  | "idea_selection_required"
  | "experiment_setup_required"
  | "experiment_planner_required"
  | "experiment_review_required";

export type WorkflowBlockingStage = {
  readonly id: string;
  readonly title: string;
};

export type WorkflowStageReadiness = {
  readonly blockingStages: readonly WorkflowBlockingStage[];
  readonly blockingStageTitles: readonly string[];
  readonly canRun: boolean;
  readonly missingExperimentInputs: readonly ExperimentSetupInputKey[];
  readonly reason: WorkflowReadinessReason;
};

type Translate = (key: TranslationKey) => string;

const experimentSetupInputKeys = ["data_path", "code_repository", "environment_notes"] as const;
type ExperimentSetupInputKey = (typeof experimentSetupInputKeys)[number];

const experimentSetupInputLabelKeys: Record<ExperimentSetupInputKey, TranslationKey> = {
  code_repository: "experimentCodeRepository",
  data_path: "experimentDataPath",
  environment_notes: "experimentEnvironmentNotes",
};

const readinessReasonKeys: Record<WorkflowReadinessReason, TranslationKey> = {
  demand_validation_required: "workflowReadinessDemandRequired",
  demand_evidence_review_required: "workflowReadinessDemandEvidenceRequired",
  demand_review_required: "workflowReadinessDemandReviewRequired",
  experiment_planner_required: "workflowReadinessExperimentPlannerRequired",
  experiment_review_required: "workflowReadinessExperimentReviewRequired",
  experiment_setup_required: "workflowReadinessExperimentSetupRequired",
  gap_prerequisites_required: "workflowReadinessGapRequired",
  idea_selection_required: "workflowReadinessIdeaSelectionRequired",
  ready: "workflowReadinessReady",
  runner_not_implemented: "workflowReadinessRunnerNotImplemented",
  status_complete: "workflowReadinessStatusComplete",
  status_running: "workflowReadinessStatusRunning",
};

function readString(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value.trim() : "";
}

function readStringArray(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim() !== "") : [];
}

function readRecordArray(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return Array.isArray(value)
    ? value.filter(
        (item): item is Record<string, unknown> =>
          typeof item === "object" && item !== null && !Array.isArray(item),
      )
    : [];
}

function findStage(stages: readonly StageCard[], agentId: string) {
  return stages.find((stage) => stage.agent_id === agentId);
}

function isComplete(stage: StageCard | undefined) {
  return stage?.status === "complete";
}

function isHumanApproved(stage: StageCard | undefined) {
  return stage?.human_approved === true;
}

function hasRecordedHumanDemandEvidence(stage: StageCard | undefined) {
  if (stage === undefined || stage.status !== "complete" || stage.human_approved !== true) {
    return false;
  }

  const verdict = readString(stage.evidence_payload, "human_demand_verdict");
  const sources = readStringArray(stage.evidence_payload, "human_demand_sources");
  return (verdict === "plausible" || verdict === "verified") && sources.length > 0;
}

function isRunnableStatus(stage: StageCard) {
  return stage.status === "pending" || stage.status === "blocked";
}

function blockingStage(stage: StageCard): WorkflowBlockingStage {
  return {
    id: stage.id,
    title: stage.title,
  };
}

function unavailableReadiness(stage: StageCard): WorkflowStageReadiness {
  if (stage.status === "complete") {
    return {
      blockingStages: [],
      blockingStageTitles: [],
      canRun: false,
      missingExperimentInputs: [],
      reason: "status_complete",
    };
  }

  if (stage.status === "running") {
    return {
      blockingStages: [],
      blockingStageTitles: [],
      canRun: false,
      missingExperimentInputs: [],
      reason: "status_running",
    };
  }

  return {
    blockingStages: [],
    blockingStageTitles: [],
    canRun: false,
    missingExperimentInputs: [],
    reason: "runner_not_implemented",
  };
}

function readyReadiness(): WorkflowStageReadiness {
  return {
    blockingStages: [],
    blockingStageTitles: [],
    canRun: true,
    missingExperimentInputs: [],
    reason: "ready",
  };
}

function blockedReadiness(
  reason: WorkflowReadinessReason,
  blockingStages: readonly WorkflowBlockingStage[] = [],
  missingExperimentInputs: readonly ExperimentSetupInputKey[] = [],
): WorkflowStageReadiness {
  return {
    blockingStages,
    blockingStageTitles: blockingStages.map((stage) => stage.title),
    canRun: false,
    missingExperimentInputs,
    reason,
  };
}

function hasSelectedIdea(stage: StageCard | undefined) {
  if (!stage || stage.status !== "complete" || stage.human_approved !== true) {
    return false;
  }

  const selectedIdeaIds = new Set(readStringArray(stage.output_payload, "selected_idea_ids"));
  const ideas = readRecordArray(stage.output_payload, "ideas");
  return ideas.some((idea) => {
    const ideaId = readString(idea, "idea_id");
    return ideaId !== "" && selectedIdeaIds.has(ideaId);
  });
}

function missingExperimentSetupInputs(stage: StageCard) {
  return experimentSetupInputKeys.filter((key) => readString(stage.input_payload, key) === "");
}

function localizedExperimentInputLabels(inputs: readonly ExperimentSetupInputKey[], t: Translate) {
  return inputs.map((input) => t(experimentSetupInputLabelKeys[input])).join(", ");
}

function missingCompletedStages(stages: readonly StageCard[], agentIds: readonly string[]) {
  return agentIds
    .map((agentId) => findStage(stages, agentId))
    .filter((stage): stage is StageCard => stage !== undefined && stage.status !== "complete")
    .map(blockingStage);
}

export function getWorkflowStageReadiness(
  stage: StageCard,
  stages: readonly StageCard[],
): WorkflowStageReadiness {
  if (!isRunnableStatus(stage)) {
    return unavailableReadiness(stage);
  }

  if (stage.agent_id === demandValidatorAgentId) {
    return readyReadiness();
  }

  const demandStage = findStage(stages, demandValidatorAgentId);

  if (stage.agent_id === literatureScoutAgentId) {
    if (!demandStage || !isComplete(demandStage)) {
      return blockedReadiness("demand_validation_required", demandStage ? [blockingStage(demandStage)] : []);
    }
    if (!isHumanApproved(demandStage)) {
      return blockedReadiness("demand_review_required", [blockingStage(demandStage)]);
    }
    return hasRecordedHumanDemandEvidence(demandStage)
      ? readyReadiness()
      : blockedReadiness("demand_evidence_review_required", [blockingStage(demandStage)]);
  }

  if (demandStage && isComplete(demandStage)) {
    if (!isHumanApproved(demandStage)) {
      return blockedReadiness("demand_review_required", [blockingStage(demandStage)]);
    }
    if (!hasRecordedHumanDemandEvidence(demandStage)) {
      return blockedReadiness("demand_evidence_review_required", [blockingStage(demandStage)]);
    }
  }

  if (stage.agent_id === ideaGeneratorAgentId) {
    const missingStages = missingCompletedStages(stages, [
      demandValidatorAgentId,
      literatureScoutAgentId,
    ]);
    return missingStages.length === 0
      ? readyReadiness()
      : blockedReadiness("gap_prerequisites_required", missingStages);
  }

  if (stage.agent_id === experimentPlannerAgentId) {
    const ideaStage = findStage(stages, ideaGeneratorAgentId);
    if (!hasSelectedIdea(ideaStage)) {
      return blockedReadiness("idea_selection_required", ideaStage ? [blockingStage(ideaStage)] : []);
    }

    const missingInputs = missingExperimentSetupInputs(stage);
    return missingInputs.length === 0
      ? readyReadiness()
      : blockedReadiness("experiment_setup_required", [], missingInputs);
  }

  if (stage.agent_id === paperMeetingWriterAgentId) {
    const experimentStage = findStage(stages, experimentPlannerAgentId);
    if (!experimentStage || !isComplete(experimentStage)) {
      return blockedReadiness("experiment_planner_required", experimentStage ? [blockingStage(experimentStage)] : []);
    }
    return isHumanApproved(experimentStage)
      ? readyReadiness()
      : blockedReadiness("experiment_review_required", [blockingStage(experimentStage)]);
  }

  return unavailableReadiness(stage);
}

export function getLocalizedWorkflowReadinessReason(
  readiness: WorkflowStageReadiness,
  t: Translate,
) {
  const baseReason = t(readinessReasonKeys[readiness.reason]);
  if (readiness.missingExperimentInputs.length > 0) {
    return `${baseReason} ${t("workflowReadinessMissingInputs")}: ${localizedExperimentInputLabels(readiness.missingExperimentInputs, t)}`;
  }
  if (readiness.blockingStageTitles.length > 0) {
    return `${baseReason} ${readiness.blockingStageTitles.join(", ")}`;
  }
  return baseReason;
}
