import type { TranslationKey } from "../i18n/i18n-context";
import { labelFromEnum } from "./format";

type Translate = (key: TranslationKey) => string;

export function localizedResearchLabel(value: string, t: Translate) {
  switch (value) {
    case "strong":
      return t("demandAssessmentStrong");
    case "plausible":
      return t("demandAssessmentPlausible");
    case "unclear":
      return t("demandAssessmentUnclear");
    case "weak":
      return t("demandAssessmentWeak");
    case "go":
      return t("demandRecommendationGo");
    case "go_with_human_review":
      return t("demandRecommendationHumanReview");
    case "needs_more_evidence":
      return t("demandRecommendationMoreEvidence");
    case "no_go":
      return t("demandRecommendationNoGo");
    case "high":
      return t("confidenceHigh");
    case "medium":
      return t("confidenceMedium");
    case "low":
      return t("confidenceLow");
    case "unknown":
      return t("confidenceUnknown");
    case "human_reviewed_sources":
      return t("sourceVerificationHumanReviewed");
    case "model_only_no_external_source_verification":
      return t("sourceVerificationModelOnly");
    default:
      return labelFromEnum(value);
  }
}
