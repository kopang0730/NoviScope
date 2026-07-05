import type { StageCard } from "../api/types";

export const demandValidatorAgentId = "demand_validator";
export const literatureScoutAgentId = "literature_scout";
export const ideaGeneratorAgentId = "idea_generator";
export const experimentPlannerAgentId = "experiment_planner";
export const paperMeetingWriterAgentId = "paper_meeting_writer";

export type StageRunAvailability = {
  readonly canRun: boolean;
  readonly reason: string;
};

export function canRunDemandValidationStage(stage: StageCard) {
  return (
    stage.agent_id === demandValidatorAgentId &&
    (stage.status === "pending" || stage.status === "blocked")
  );
}

export function canRunLiteratureScoutStage(stage: StageCard) {
  return (
    stage.agent_id === literatureScoutAgentId &&
    (stage.status === "pending" || stage.status === "blocked")
  );
}

export function canRunIdeaGeneratorStage(stage: StageCard) {
  return (
    stage.agent_id === ideaGeneratorAgentId &&
    (stage.status === "pending" || stage.status === "blocked")
  );
}

export function canRunExperimentPlannerStage(stage: StageCard) {
  return (
    stage.agent_id === experimentPlannerAgentId &&
    (stage.status === "pending" || stage.status === "blocked")
  );
}

export function canRunPaperMeetingWriterStage(stage: StageCard) {
  return (
    stage.agent_id === paperMeetingWriterAgentId &&
    (stage.status === "pending" || stage.status === "blocked")
  );
}

export function canRunStage(stage: StageCard) {
  return (
    canRunDemandValidationStage(stage) ||
    canRunLiteratureScoutStage(stage) ||
    canRunIdeaGeneratorStage(stage) ||
    canRunExperimentPlannerStage(stage) ||
    canRunPaperMeetingWriterStage(stage)
  );
}

function readPayloadString(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

export function getStageRunAvailability(stage: StageCard): StageRunAvailability {
  if (canRunDemandValidationStage(stage)) {
    return {
      canRun: true,
      reason: "Ready if an active OpenAI-compatible or custom provider is configured.",
    };
  }

  if (canRunLiteratureScoutStage(stage)) {
    return {
      canRun: true,
      reason: "Ready after demand validation completes; backend blocks if the prerequisite is missing.",
    };
  }

  if (canRunIdeaGeneratorStage(stage)) {
    return {
      canRun: true,
      reason: (
        "Ready after demand validation and literature scouting complete; human selection is "
        + "required before experiment design."
      ),
    };
  }

  if (canRunExperimentPlannerStage(stage)) {
    const detail = readPayloadString(stage.evidence_payload, "blocking_detail");
    return {
      canRun: true,
      reason:
        detail ||
        "Ready after a human-approved idea plus data path, code repository, and environment notes.",
    };
  }

  if (canRunPaperMeetingWriterStage(stage)) {
    const detail = readPayloadString(stage.evidence_payload, "blocking_detail");
    return {
      canRun: true,
      reason:
        detail ||
        "Ready after Experiment Planner completes; generated drafts remain review-only.",
    };
  }

  if (stage.status === "blocked") {
    const detail = readPayloadString(stage.evidence_payload, "blocking_detail");
    return {
      canRun: false,
      reason: detail || "This stage is blocked. Open the stage to review the reason.",
    };
  }

  if (stage.status === "complete") {
    return {
      canRun: false,
      reason: "Completed. Review the output and human approval before continuing.",
    };
  }

  if (stage.status === "running") {
    return {
      canRun: false,
      reason: "Already running.",
    };
  }

  return {
    canRun: false,
    reason: "No runner has been implemented for this workflow stage yet.",
  };
}
