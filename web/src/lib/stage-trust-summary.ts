import type { StageCard } from "../api/types";

export type StageTrustSummary = {
  readonly noExperimentResults: boolean;
  readonly planOnly: boolean;
  readonly requiresHumanReview: boolean;
  readonly reviewItems: readonly string[];
  readonly sourceStageIds: Readonly<Record<string, string>>;
  readonly warnings: readonly string[];
};

function readStringArray(payload: Readonly<Record<string, unknown>>, key: string): readonly string[] {
  const value = payload[key];
  return Array.isArray(value) ? value.filter((item) => typeof item === "string" && item.length > 0) : [];
}

function readBoolean(payload: Readonly<Record<string, unknown>>, key: string): boolean {
  return payload[key] === true;
}

function readSourceStageIds(payload: Readonly<Record<string, unknown>>): Readonly<Record<string, string>> {
  const value = payload.source_stage_ids;
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return {};
  }

  const sourceStageIds: Record<string, string> = {};
  for (const [key, item] of Object.entries(value)) {
    if (typeof item === "string" && item.length > 0) {
      sourceStageIds[key] = item;
    }
  }
  return sourceStageIds;
}

function uniqueStrings(items: readonly string[]): readonly string[] {
  return [...new Set(items)];
}

export function buildStageTrustSummary(stage: StageCard): StageTrustSummary {
  const reviewItems = uniqueStrings([
    ...readStringArray(stage.output_payload, "human_review_required"),
    ...readStringArray(stage.output_payload, "suggested_human_checklist"),
  ]);
  const sourceStageIds = {
    ...readSourceStageIds(stage.evidence_payload),
    ...readSourceStageIds(stage.output_payload),
  };
  const noExperimentResults =
    readBoolean(stage.output_payload, "no_experiment_results") ||
    readBoolean(stage.evidence_payload, "no_experiment_results") ||
    readStringArray(stage.output_payload, "experiment_results_not_available").length > 0;

  return {
    noExperimentResults,
    planOnly: readBoolean(stage.output_payload, "plan_only") || readBoolean(stage.evidence_payload, "plan_only"),
    requiresHumanReview: readBoolean(stage.evidence_payload, "requires_human_review") || reviewItems.length > 0,
    reviewItems,
    sourceStageIds,
    warnings: readStringArray(stage.output_payload, "warnings"),
  };
}
