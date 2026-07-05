import type { StageCard } from "../api/types";
import type { TranslationKey } from "../i18n/i18n-context";
import {
  canRunDemandValidationStage,
  canRunExperimentPlannerStage,
  canRunIdeaGeneratorStage,
  canRunLiteratureScoutStage,
  canRunPaperMeetingWriterStage,
} from "./stages";

type Translate = (key: TranslationKey) => string;

function readPayloadString(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

export function getLocalizedStageRunReason(stage: StageCard, t: Translate) {
  if (canRunDemandValidationStage(stage)) {
    return t("stageRunReasonDemandReady");
  }

  if (canRunLiteratureScoutStage(stage)) {
    return t("stageRunReasonLiteratureReady");
  }

  if (canRunIdeaGeneratorStage(stage)) {
    return t("stageRunReasonIdeaReady");
  }

  if (canRunExperimentPlannerStage(stage)) {
    return readPayloadString(stage.evidence_payload, "blocking_detail") || t("stageRunReasonExperimentReady");
  }

  if (canRunPaperMeetingWriterStage(stage)) {
    return readPayloadString(stage.evidence_payload, "blocking_detail") || t("stageRunReasonPaperReady");
  }

  if (stage.status === "blocked") {
    return readPayloadString(stage.evidence_payload, "blocking_detail") || t("stageRunReasonBlocked");
  }

  if (stage.status === "complete") {
    return t("stageRunReasonComplete");
  }

  if (stage.status === "running") {
    return t("stageRunReasonRunning");
  }

  return t("stageRunReasonNoRunner");
}
