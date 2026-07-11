import type { WorkflowNextAction } from "../api/types";
import { translations, type Language, type TranslationKey } from "../i18n/translations";

export type WorkflowActionCommand = "open_providers" | "open_stage" | "run" | "wait";

export type WorkflowActionView = {
  readonly command: WorkflowActionCommand;
  readonly disabled: boolean;
  readonly reason: string;
  readonly responsible: string;
  readonly title: string;
};

export function workflowActionStagePath(action: WorkflowNextAction, questId: string) {
  const stagePath = `/stages/${action.stage_id}?quest=${questId}`;
  switch (action.action_type) {
    case "review_stage":
      return `${stagePath}#review`;
    case "resolve_blocker":
      return action.blocking_reason === "human_review_rejected"
        ? `${stagePath}#review`
        : `${stagePath}#artifacts`;
    case "configure_provider":
    case "run_stage":
    case "wait_for_stage":
      return stagePath;
    default:
      return unreachableActionType(action.action_type);
  }
}

const blockingReasonKeys: Readonly<Record<string, TranslationKey>> = {
  demand_evidence_review_required: "workflowActionReasonDemandEvidenceReviewRequired",
  demand_validation_incomplete: "workflowActionReasonDemandValidationIncomplete",
  demand_validation_review_required: "workflowActionReasonDemandValidationReviewRequired",
  experiment_planner_review_required: "workflowActionReasonExperimentPlannerReviewRequired",
  experiment_prerequisites_incomplete: "workflowActionReasonExperimentPrerequisitesIncomplete",
  gap_prerequisites_incomplete: "workflowActionReasonGapPrerequisitesIncomplete",
  human_review_required: "workflowActionReasonHumanReviewRequired",
  human_review_rejected: "workflowActionReasonHumanReviewRejected",
  inactive_provider: "workflowActionReasonInactiveProvider",
  idea_selection_required: "workflowActionReasonIdeaSelectionRequired",
  missing_experiment_inputs: "workflowActionReasonMissingExperimentInputs",
  missing_provider: "workflowActionReasonMissingProvider",
  paper_prerequisites_incomplete: "workflowActionReasonPaperPrerequisitesIncomplete",
  runner_error: "workflowActionReasonRunnerError",
  runner_not_implemented: "workflowActionReasonRunnerNotImplemented",
  stage_already_complete: "workflowActionReasonStageAlreadyComplete",
  stage_already_running: "workflowActionReasonStageAlreadyRunning",
  unsupported_provider: "workflowActionReasonUnsupportedProvider",
};

function unreachableActionType(actionType: never): never {
  throw new Error(`Unsupported workflow action type: ${actionType}`);
}

function localizedReason(action: WorkflowNextAction, language: Language) {
  if (!action.blocking_reason) {
    return translations[language].workflowActionReasonReady;
  }

  const key = blockingReasonKeys[action.blocking_reason];
  return key ? translations[language][key] : action.detail || action.label;
}

function responsibleAgent(action: WorkflowNextAction, language: Language) {
  return `${translations[language].workflowActionResponsibleAgent}: ${action.stage_title}`;
}

function title(key: TranslationKey, action: WorkflowNextAction, language: Language) {
  return `${translations[language][key]}: ${action.stage_title}`;
}

export function buildWorkflowActionView(
  action: WorkflowNextAction,
  language: Language,
): WorkflowActionView {
  const reason = localizedReason(action, language);

  switch (action.action_type) {
    case "configure_provider":
      return {
        command: "open_providers",
        disabled: false,
        reason,
        responsible: translations[language].workflowActionResponsibleResearcher,
        title: title("workflowActionConfigureProvider", action, language),
      };
    case "resolve_blocker":
      return {
        command: "open_stage",
        disabled: false,
        reason,
        responsible: translations[language].workflowActionResponsibleResearcher,
        title: title("workflowActionResolveBlocker", action, language),
      };
    case "review_stage":
      return {
        command: "open_stage",
        disabled: false,
        reason,
        responsible: translations[language].workflowActionResponsibleSupervisor,
        title: title("workflowActionReviewStage", action, language),
      };
    case "run_stage":
      return {
        command: "run",
        disabled: !action.can_run,
        reason,
        responsible: responsibleAgent(action, language),
        title: title("workflowActionRunStage", action, language),
      };
    case "wait_for_stage":
      return {
        command: "wait",
        disabled: true,
        reason,
        responsible: responsibleAgent(action, language),
        title: title("workflowActionWaitForStage", action, language),
      };
    default:
      return unreachableActionType(action.action_type);
  }
}
