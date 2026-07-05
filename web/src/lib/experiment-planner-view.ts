import type { StageCard, StageConfidence } from "../api/types";
import { experimentPlannerAgentId } from "./stages";

export type ExperimentPlannerSetup = {
  readonly codeRepository: string;
  readonly dataPath: string;
  readonly environmentNotes: string;
};

export type ExperimentPlannerView = {
  readonly ablationVariables: readonly string[];
  readonly baselinesToReproduce: readonly string[];
  readonly computeRequirements: string;
  readonly confidence: StageConfidence;
  readonly dataAvailabilityStatus: string;
  readonly datasetsNeeded: readonly string[];
  readonly expectedFigures: readonly string[];
  readonly expectedTables: readonly string[];
  readonly failureRisks: readonly string[];
  readonly firstRunnableScriptPlan: readonly string[];
  readonly metrics: readonly string[];
  readonly summary: string;
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

export function readExperimentPlannerSetup(stage: StageCard): ExperimentPlannerSetup {
  return {
    codeRepository: readString(stage.input_payload, "code_repository"),
    dataPath: readString(stage.input_payload, "data_path"),
    environmentNotes: readString(stage.input_payload, "environment_notes"),
  };
}

export function buildExperimentPlannerView(stage: StageCard): ExperimentPlannerView | null {
  if (stage.agent_id !== experimentPlannerAgentId || stage.status !== "complete") {
    return null;
  }

  return {
    ablationVariables: readStringArray(stage.output_payload, "ablation_variables"),
    baselinesToReproduce: readStringArray(stage.output_payload, "baselines_to_reproduce"),
    computeRequirements: readString(stage.output_payload, "compute_requirements"),
    confidence: readConfidence(stage.output_payload, "confidence"),
    dataAvailabilityStatus: readString(stage.output_payload, "data_availability_status"),
    datasetsNeeded: readStringArray(stage.output_payload, "datasets_needed"),
    expectedFigures: readStringArray(stage.output_payload, "expected_figures"),
    expectedTables: readStringArray(stage.output_payload, "expected_tables"),
    failureRisks: readStringArray(stage.output_payload, "failure_risks"),
    firstRunnableScriptPlan: readStringArray(stage.output_payload, "first_runnable_script_plan"),
    metrics: readStringArray(stage.output_payload, "metrics"),
    summary: readString(stage.output_payload, "summary") || stage.summary,
    warnings: readStringArray(stage.output_payload, "warnings"),
  };
}
