import { describe, expect, it } from "vitest";
import type {
  Provider,
  StageCard,
  WorkflowAgentCapability,
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

    const presentation = buildMacroPhasePresentation(
      phase,
      readiness,
      [stage],
      (key: TranslationKey) => key,
    );

    expect(presentation.state).toBe("runnable");
  });
});
