import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type {
  Provider,
  StageCard,
  WorkflowAgentCapability,
  WorkflowNextAction,
} from "../api/types";
import { I18nProvider } from "../i18n/i18n-context";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import { ResearchCanvas } from "./research-canvas";

const timestamp = "2026-07-10T00:00:00Z";
const provider: Provider = {
  base_url: "https://model.example.com/v1",
  created_at: timestamp,
  default_model: "research-model",
  id: "provider-1",
  is_active: true,
  kind: "openai_compatible",
  name: "Lab Model",
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

function stage(agentId: string, id: string, title: string): StageCard {
  return {
    agent_id: agentId,
    confidence: "unknown",
    created_at: timestamp,
    evidence_payload: {},
    human_approved: null,
    id,
    input_payload: {},
    output_payload: {},
    quest_id: "quest-1",
    review_notes: "",
    status: "pending",
    summary: "",
    title,
    updated_at: timestamp,
  };
}

function capability(currentStage: StageCard): WorkflowAgentCapability {
  return {
    agent_id: currentStage.agent_id,
    automation_status: "implemented",
    display_name: currentStage.title,
    provider_requirement: "model_provider",
    stage_runner_available: true,
    status_detail: "Runnable.",
    tool_permissions: [],
  };
}

function nextAction(currentStage: StageCard): WorkflowNextAction {
  return {
    action_type: "run_stage",
    agent_id: currentStage.agent_id,
    blocking_reason: "",
    can_run: true,
    detail: "Ready to run.",
    label: `Run ${currentStage.title}`,
    priority: 1,
    stage_id: currentStage.id,
    stage_status: currentStage.status,
    stage_title: currentStage.title,
  };
}

describe("ResearchCanvas", () => {
  afterEach(cleanup);

  beforeEach(() => {
    window.localStorage.setItem("noviscope-language", "en");
  });

  it("selects the phase of a newly advanced authoritative next action", () => {
    const demandStage = stage("demand_validator", "stage-demand", "Demand validation");
    const ideaStage = stage("idea_generator", "stage-idea", "Gap and hypothesis");
    const stages = [demandStage, ideaStage];
    const capabilities = stages.map(capability);
    const view = render(
      <MemoryRouter>
        <I18nProvider>
          <ResearchCanvas
            capabilities={capabilities}
            currentUserId="user-1"
            nextAction={nextAction(demandStage)}
            onRunStage={vi.fn()}
            providerReadinessData={readiness}
            runningStageId={null}
            stages={stages}
          />
        </I18nProvider>
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: demandStage.title })).toBeInTheDocument();

    view.rerender(
      <MemoryRouter>
        <I18nProvider>
          <ResearchCanvas
            capabilities={capabilities}
            currentUserId="user-1"
            nextAction={nextAction(ideaStage)}
            onRunStage={vi.fn()}
            providerReadinessData={readiness}
            runningStageId={null}
            stages={stages}
          />
        </I18nProvider>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: ideaStage.title })).toBeInTheDocument();
  });
});
