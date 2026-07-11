import { describe, expect, it } from "vitest";
import type {
  Provider,
  StageCard,
  WorkflowAgentCapability,
  WorkflowNextAction,
} from "../api/types";
import type { TranslationKey } from "../i18n/i18n-context";
import type { ProviderReadinessData } from "./provider-readiness-data";
import { buildMacroPhasePresentation } from "./research-phase-projection";
import { buildMacroPhaseViews } from "./research-workbench";

const timestamp = "2026-07-10T00:00:00Z";
const stage: StageCard = {
  agent_id: "demand_validator",
  confidence: "unknown",
  created_at: timestamp,
  evidence_payload: {},
  human_approved: null,
  id: "stage-demand",
  input_payload: {},
  output_payload: {},
  quest_id: "quest-1",
  review_notes: "",
  status: "pending",
  summary: "",
  title: "Demand Validator",
  updated_at: timestamp,
};
const capability: WorkflowAgentCapability = {
  agent_id: stage.agent_id,
  automation_status: "implemented",
  display_name: stage.title,
  provider_requirement: "model_provider",
  stage_runner_available: true,
  status_detail: "Runnable with a compatible provider.",
  tool_permissions: [],
};
const provider: Provider = {
  base_url: "https://model.example.com/v1",
  api_mode: "auto",
  created_at: timestamp,
  default_model: "claude-research",
  id: "provider-anthropic",
  is_active: true,
  kind: "anthropic",
  name: "Anthropic Lab",
  owner_user_id: null,
  scope: "shared",
  updated_at: timestamp,
};
const readiness: ProviderReadinessData = {
  assignments: [],
  error: null,
  loaded: true,
  loading: false,
  providers: [provider],
};

describe("research phase provider projection", () => {
  it("projects a model-backed phase as runnable with only Anthropic active", () => {
    const phase = buildMacroPhaseViews([stage], [capability])[0];
    expect(phase).toBeDefined();
    if (!phase) {
      return;
    }

    const presentation = buildMacroPhasePresentation({
      nextAction: null,
      phase,
      providerReadinessData: readiness,
      stages: [stage],
      t: (key: TranslationKey) => key,
    });

    expect(presentation.state).toBe("runnable");
  });

  it("projects a rejected human gate as blocked instead of complete", () => {
    const rejectedStage = {
      ...stage,
      human_approved: false,
      status: "complete" as const,
      summary: "Demand evidence was rejected.",
    };
    const phase = buildMacroPhaseViews([rejectedStage], [capability])[0];
    expect(phase).toBeDefined();
    if (!phase) {
      return;
    }

    const presentation = buildMacroPhasePresentation({
      nextAction: null,
      phase,
      providerReadinessData: readiness,
      stages: [rejectedStage],
      t: (key: TranslationKey) => key,
    });

    expect(presentation.state).toBe("blocked");
  });

  it("projects a complete phase with an authoritative blocker as blocked", () => {
    const completeStage = {
      ...stage,
      human_approved: true,
      status: "complete" as const,
      summary: "Demand approved without a recorded source.",
    };
    const phase = buildMacroPhaseViews([completeStage], [capability])[0];
    const nextAction: WorkflowNextAction = {
      action_type: "resolve_blocker",
      agent_id: completeStage.agent_id,
      blocking_reason: "demand_evidence_review_required",
      can_run: false,
      detail: "Record at least one demand evidence source.",
      label: "Resolve demand evidence blocker",
      priority: 2,
      stage_id: completeStage.id,
      stage_status: completeStage.status,
      stage_title: completeStage.title,
    };
    expect(phase).toBeDefined();
    if (!phase) {
      return;
    }

    const presentation = buildMacroPhasePresentation({
      nextAction,
      phase,
      providerReadinessData: readiness,
      stages: [completeStage],
      t: (key: TranslationKey) => key,
    });

    expect(presentation.state).toBe("blocked");
    expect(presentation.signal).toBe(nextAction.detail);
  });

  it("projects a provider configuration action as a blocked phase", () => {
    const phase = buildMacroPhaseViews([stage], [capability])[0];
    const nextAction: WorkflowNextAction = {
      action_type: "configure_provider",
      agent_id: stage.agent_id,
      blocking_reason: "missing_provider",
      can_run: false,
      detail: "Configure an active supported provider before running this stage.",
      label: "Configure provider for Demand Validator",
      priority: 1,
      stage_id: stage.id,
      stage_status: stage.status,
      stage_title: stage.title,
    };
    expect(phase).toBeDefined();
    if (!phase) {
      return;
    }

    const presentation = buildMacroPhasePresentation({
      nextAction,
      phase,
      providerReadinessData: { ...readiness, providers: [] },
      stages: [stage],
      t: (key: TranslationKey) => key,
    });

    expect(presentation.state).toBe("blocked");
    expect(presentation.signal).toBe(nextAction.detail);
  });

  it("projects a reopened rejected gate as runnable when the backend allows a rerun", () => {
    const reopenedStage = {
      ...stage,
      human_approved: false,
      status: "blocked" as const,
      summary: "Demand validation was reopened for rerun.",
    };
    const phase = buildMacroPhaseViews([reopenedStage], [capability])[0];
    const nextAction: WorkflowNextAction = {
      action_type: "run_stage",
      agent_id: reopenedStage.agent_id,
      blocking_reason: "",
      can_run: true,
      detail: "Stage is ready to run.",
      label: "Run Demand Validator",
      priority: 1,
      stage_id: reopenedStage.id,
      stage_status: reopenedStage.status,
      stage_title: reopenedStage.title,
    };
    expect(phase).toBeDefined();
    if (!phase) {
      return;
    }

    const presentation = buildMacroPhasePresentation({
      nextAction,
      phase,
      providerReadinessData: readiness,
      stages: [reopenedStage],
      t: (key: TranslationKey) => key,
    });

    expect(presentation.state).toBe("runnable");
  });
});
