import type { StageCard, StageConfidence } from "../api/types";
import { ideaGeneratorAgentId } from "./stages";

export type GapSeverity = "high" | "medium" | "low";
export type GapEvidenceType = "paper_limitations" | "metadata_inference" | "human_context";
export type IdeaSelectionStatus = "pending_human_selection" | "selected_for_experiment_design";

export type GapItem = {
  readonly description: string;
  readonly evidenceType: GapEvidenceType;
  readonly gapTitle: string;
  readonly severity: GapSeverity;
  readonly supportingPapers: readonly string[];
};

export type IdeaItem = {
  readonly applicationValue: StageConfidence;
  readonly basedOnWhichPapers: readonly string[];
  readonly confidence: StageConfidence;
  readonly coreHypothesis: string;
  readonly expectedImprovement: string;
  readonly experimentFeasibility: StageConfidence;
  readonly ideaId: string;
  readonly ideaTitle: string;
  readonly noveltyRisk: StageConfidence;
  readonly requiredBaseline: string;
  readonly requiredData: string;
};

export type IdeaGeneratorView = {
  readonly confidence: StageConfidence;
  readonly gaps: readonly GapItem[];
  readonly ideas: readonly IdeaItem[];
  readonly selectedIdeaIds: readonly string[];
  readonly selectionStatus: IdeaSelectionStatus;
  readonly sourceStageIds: Record<string, string>;
  readonly summary: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStageConfidence(value: string): value is StageConfidence {
  return value === "high" || value === "medium" || value === "low" || value === "unknown";
}

function isGapSeverity(value: string): value is GapSeverity {
  return value === "high" || value === "medium" || value === "low";
}

function isGapEvidenceType(value: string): value is GapEvidenceType {
  return value === "paper_limitations" || value === "metadata_inference" || value === "human_context";
}

function isIdeaSelectionStatus(value: string): value is IdeaSelectionStatus {
  return value === "pending_human_selection" || value === "selected_for_experiment_design";
}

function readString(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

function readStringArray(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function readConfidence(payload: Record<string, unknown>, key: string) {
  const value = readString(payload, key);
  return isStageConfidence(value) ? value : "unknown";
}

function readGap(value: unknown): GapItem | null {
  if (!isRecord(value)) {
    return null;
  }

  const severity = readString(value, "severity");
  const evidenceType = readString(value, "evidence_type");

  return {
    description: readString(value, "description"),
    evidenceType: isGapEvidenceType(evidenceType) ? evidenceType : "metadata_inference",
    gapTitle: readString(value, "gap_title"),
    severity: isGapSeverity(severity) ? severity : "medium",
    supportingPapers: readStringArray(value, "supporting_papers"),
  };
}

function readIdea(value: unknown): IdeaItem | null {
  if (!isRecord(value)) {
    return null;
  }

  return {
    applicationValue: readConfidence(value, "application_value"),
    basedOnWhichPapers: readStringArray(value, "based_on_which_papers"),
    confidence: readConfidence(value, "confidence"),
    coreHypothesis: readString(value, "core_hypothesis"),
    expectedImprovement: readString(value, "expected_improvement"),
    experimentFeasibility: readConfidence(value, "experiment_feasibility"),
    ideaId: readString(value, "idea_id"),
    ideaTitle: readString(value, "idea_title"),
    noveltyRisk: readConfidence(value, "novelty_risk"),
    requiredBaseline: readString(value, "required_baseline"),
    requiredData: readString(value, "required_data"),
  };
}

export function buildIdeaGeneratorView(stage: StageCard): IdeaGeneratorView | null {
  if (stage.agent_id !== ideaGeneratorAgentId || stage.status !== "complete") {
    return null;
  }

  const gaps = Array.isArray(stage.output_payload.gaps)
    ? stage.output_payload.gaps.map(readGap).filter((gap): gap is GapItem => gap !== null)
    : [];
  const ideas = Array.isArray(stage.output_payload.ideas)
    ? stage.output_payload.ideas.map(readIdea).filter((idea): idea is IdeaItem => idea !== null)
    : [];
  const selectionStatusValue = readString(stage.output_payload, "selection_status");
  const sourceStageIds = isRecord(stage.output_payload.source_stage_ids)
    ? stage.output_payload.source_stage_ids
    : {};

  return {
    confidence: isStageConfidence(stage.confidence) ? stage.confidence : "unknown",
    gaps,
    ideas,
    selectedIdeaIds: readStringArray(stage.output_payload, "selected_idea_ids"),
    selectionStatus: isIdeaSelectionStatus(selectionStatusValue)
      ? selectionStatusValue
      : "pending_human_selection",
    sourceStageIds: Object.fromEntries(
      Object.entries(sourceStageIds).filter(
        (entry): entry is [string, string] => typeof entry[1] === "string",
      ),
    ),
    summary: readString(stage.output_payload, "summary") || stage.summary,
  };
}
