import type { StageCard, StageConfidence } from "../api/types";
import { readSourceStageIds, type SourceStageIds } from "./source-stage-ids";
import { paperMeetingWriterAgentId } from "./stages";

export type MarkdownArtifact = {
  readonly content: string;
  readonly filename: string;
  readonly key: string;
  readonly titleKey:
    | "chineseResearchBrief"
    | "englishResearchBrief"
    | "meetingOutline"
    | "ieeePaperSkeleton";
};

export type PaperMeetingWriterView = {
  readonly artifacts: readonly MarkdownArtifact[];
  readonly confidence: StageConfidence;
  readonly experimentResultsNotAvailable: readonly string[];
  readonly humanReviewRequired: readonly string[];
  readonly modelGeneratedHypotheses: readonly string[];
  readonly sourceStageIds: SourceStageIds;
  readonly summary: string;
  readonly verifiedFacts: readonly string[];
  readonly warnings: readonly string[];
};

function isStageConfidence(value: string): value is StageConfidence {
  return value === "high" || value === "medium" || value === "low" || value === "unknown";
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

export function buildPaperMeetingWriterView(stage: StageCard): PaperMeetingWriterView | null {
  if (stage.agent_id !== paperMeetingWriterAgentId || stage.status !== "complete") {
    return null;
  }

  return {
    artifacts: [
      {
        content: readString(stage.output_payload, "chinese_research_brief_markdown"),
        filename: "chinese-research-brief.md",
        key: "chinese_research_brief_markdown",
        titleKey: "chineseResearchBrief",
      },
      {
        content: readString(stage.output_payload, "english_research_brief_markdown"),
        filename: "english-research-brief.md",
        key: "english_research_brief_markdown",
        titleKey: "englishResearchBrief",
      },
      {
        content: readString(stage.output_payload, "meeting_outline_markdown"),
        filename: "group-meeting-outline.md",
        key: "meeting_outline_markdown",
        titleKey: "meetingOutline",
      },
      {
        content: readString(stage.output_payload, "ieee_paper_skeleton_markdown"),
        filename: "ieee-paper-skeleton.md",
        key: "ieee_paper_skeleton_markdown",
        titleKey: "ieeePaperSkeleton",
      },
    ],
    confidence: readConfidence(stage.output_payload, "confidence"),
    experimentResultsNotAvailable: readStringArray(
      stage.output_payload,
      "experiment_results_not_available",
    ),
    humanReviewRequired: readStringArray(stage.output_payload, "human_review_required"),
    modelGeneratedHypotheses: readStringArray(stage.output_payload, "model_generated_hypotheses"),
    sourceStageIds: readSourceStageIds(stage.output_payload),
    summary: readString(stage.output_payload, "summary") || stage.summary,
    verifiedFacts: readStringArray(stage.output_payload, "verified_facts"),
    warnings: readStringArray(stage.output_payload, "warnings"),
  };
}
