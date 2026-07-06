import type { StageCard } from "../api/types";
import type { TranslationKey } from "../i18n/i18n-context";
import { labelFromEnum } from "./format";

type Translate = (key: TranslationKey) => string;

function safeFilenamePart(value: string) {
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || "stage";
}

function longestBacktickRun(value: string) {
  const runs = value.match(/`+/g);
  return runs ? Math.max(...runs.map((run) => run.length)) : 0;
}

function fencedBlock(language: string, value: unknown) {
  const content = JSON.stringify(value, null, 2);
  const fence = "`".repeat(Math.max(3, longestBacktickRun(content) + 1));
  return `${fence}${language}\n${content}\n${fence}`;
}

export function buildStageReviewPacketFilename(stage: StageCard) {
  return `noviscope-${safeFilenamePart(stage.title)}-${safeFilenamePart(stage.id)}-review-packet.md`;
}

export function buildStageReviewPacketMarkdown(stage: StageCard, t: Translate) {
  const humanApproval =
    stage.human_approved === true
      ? t("stageReviewApproved")
      : stage.human_approved === false
        ? t("stageReviewRejected")
        : t("stageReviewPending");

  return [
    `# ${stage.title}`,
    "",
    `- ${t("stageDetailAgentId")}: ${stage.agent_id}`,
    `- ${t("stageStatus")}: ${labelFromEnum(stage.status)}`,
    `- ${t("stageConfidence")}: ${labelFromEnum(stage.confidence)}`,
    `- ${t("stageHumanApproval")}: ${humanApproval}`,
    `- ${t("created")}: ${stage.created_at}`,
    `- ${t("updated")}: ${stage.updated_at}`,
    "",
    `## ${t("stageSummary")}`,
    "",
    stage.summary || t("noSummaryYet"),
    "",
    `## ${t("reviewNotes")}`,
    "",
    stage.review_notes || t("stageReviewNoNotes"),
    "",
    `## ${t("stageInputPayload")}`,
    "",
    fencedBlock("json", stage.input_payload),
    "",
    `## ${t("stageOutputPayload")}`,
    "",
    fencedBlock("json", stage.output_payload),
    "",
    `## ${t("stageEvidencePayload")}`,
    "",
    fencedBlock("json", stage.evidence_payload),
    "",
  ].join("\n");
}
