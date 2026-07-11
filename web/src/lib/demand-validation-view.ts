import type { StageCard } from "../api/types";
import { demandValidatorAgentId } from "./stages";

export type DemandValidationView = {
  readonly assessment: string;
  readonly confidence: string;
  readonly evidenceForDemand: readonly string[];
  readonly goNoGoRecommendation: string;
  readonly missingEvidence: readonly string[];
  readonly nextStep: string;
  readonly realWorldScenario: string;
  readonly risks: readonly string[];
  readonly sourcePolicy: string;
  readonly sourceVerification: string;
  readonly suggestedHumanChecklist: readonly string[];
  readonly targetUserOrCustomer: string;
};

function readString(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function readStringArray(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return Array.isArray(value) ? value.filter(isString) : [];
}

function sourceVerification(stage: StageCard) {
  const humanReviewed = stage.evidence_payload.human_demand_reviewed === true;
  const humanSources = readStringArray(stage.evidence_payload, "human_demand_sources");
  if (humanReviewed && humanSources.length > 0) {
    return "human_reviewed_sources";
  }
  return readString(stage.evidence_payload, "source_policy");
}

export function buildDemandValidationView(stage: StageCard): DemandValidationView | null {
  if (stage.agent_id !== demandValidatorAgentId || stage.status !== "complete") {
    return null;
  }

  return {
    assessment: readString(stage.output_payload, "demand_assessment"),
    confidence: stage.confidence,
    evidenceForDemand: readStringArray(stage.output_payload, "evidence_for_demand"),
    goNoGoRecommendation: readString(stage.output_payload, "go_or_no_go_recommendation"),
    missingEvidence: readStringArray(stage.output_payload, "missing_evidence"),
    nextStep: readString(stage.output_payload, "next_step"),
    realWorldScenario: readString(stage.output_payload, "real_world_scenario"),
    risks: readStringArray(stage.output_payload, "risks"),
    sourcePolicy: readString(stage.evidence_payload, "source_policy"),
    sourceVerification: sourceVerification(stage),
    suggestedHumanChecklist: readStringArray(stage.output_payload, "suggested_human_checklist"),
    targetUserOrCustomer: readString(stage.output_payload, "target_user_or_customer"),
  };
}
