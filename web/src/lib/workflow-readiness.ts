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
  | "gap_prerequisites_required"
  | "idea_selection_required"
  | "experiment_setup_required"
  | "experiment_planner_required";

export type WorkflowStageReadiness = {
  readonly blockingStageTitles: readonly string[];
  readonly canRun: boolean;
  readonly missingExperimentInputs: readonly string[];
  readonly reason: WorkflowReadinessReason;
};

type Translate = (key: TranslationKey) => string;

const experimentSetupInputKeys = ["data_path", "code_repository", "environment_notes"] as const;

const readinessReasonKeys: Record<WorkflowReadinessReason, TranslationKey> = {
  demand_validation_required: "workflowReadinessDemandRequired",
  demand_review_required: "workflowReadinessDemandReviewRequired",
  experiment_planner_required: "workflowReadinessExperimentPlannerRequired",
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

function isRunnableStatus(stage: StageCard) {
  return stage.status === "pending" || stage.status === "blocked";
}

function unavailableReadiness(stage: StageCard): WorkflowStageReadiness {
  if (stage.status === "complete") {
    return {
      blockingStageTitles: [],
      canRun: false,
      missingExperimentInputs: [],
      reason: "status_complete",
    };
  }

  if (stage.status === "running") {
    return {
      blockingStageTitles: [],
      canRun: false,
      missingExperimentInputs: [],
      reason: "status_running",
    };
  }

  return {
    blockingStageTitles: [],
    canRun: false,
    missingExperimentInputs: [],
    reason: "runner_not_implemented",
  };
}

function readyReadiness(): WorkflowStageReadiness {
  return {
    blockingStageTitles: [],
    canRun: true,
    missingExperimentInputs: [],
    reason: "ready",
  };
}

function blockedReadiness(
  reason: WorkflowReadinessReason,
  blockingStageTitles: readonly string[] = [],
  missingExperimentInputs: readonly string[] = [],
): WorkflowStageReadiness {
  return {
    blockingStageTitles,
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

function missingCompletedStageTitles(stages: readonly StageCard[], agentIds: readonly string[]) {
  return agentIds
    .map((agentId) => findStage(stages, agentId))
    .filter((stage): stage is StageCard => stage !== undefined && stage.status !== "complete")
    .map((stage) => stage.title);
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
      return blockedReadiness("demand_validation_required", demandStage ? [demandStage.title] : []);
    }
    return isHumanApproved(demandStage)
      ? readyReadiness()
      : blockedReadiness("demand_review_required", [demandStage.title]);
  }

  if (demandStage && isComplete(demandStage) && !isHumanApproved(demandStage)) {
    return blockedReadiness("demand_review_required", [demandStage.title]);
  }

  if (stage.agent_id === ideaGeneratorAgentId) {
    const missingStages = missingCompletedStageTitles(stages, [
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
      return blockedReadiness("idea_selection_required", ideaStage ? [ideaStage.title] : []);
    }

    const missingInputs = missingExperimentSetupInputs(stage);
    return missingInputs.length === 0
      ? readyReadiness()
      : blockedReadiness("experiment_setup_required", [], missingInputs);
  }

  if (stage.agent_id === paperMeetingWriterAgentId) {
    const experimentStage = findStage(stages, experimentPlannerAgentId);
    return isComplete(experimentStage)
      ? readyReadiness()
      : blockedReadiness("experiment_planner_required", experimentStage ? [experimentStage.title] : []);
  }

  return unavailableReadiness(stage);
}

export function getLocalizedWorkflowReadinessReason(
  readiness: WorkflowStageReadiness,
  t: Translate,
) {
  const baseReason = t(readinessReasonKeys[readiness.reason]);
  if (readiness.missingExperimentInputs.length > 0) {
    return `${baseReason} ${t("workflowReadinessMissingInputs")}: ${readiness.missingExperimentInputs.join(", ")}`;
  }
  if (readiness.blockingStageTitles.length > 0) {
    return `${baseReason} ${readiness.blockingStageTitles.join(", ")}`;
  }
  return baseReason;
}
