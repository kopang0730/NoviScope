import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { Provider, StageCard, WorkflowAgentCapability } from "../api/types";
import { I18nProvider } from "../i18n/i18n-context";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import {
  buildMacroPhaseViews,
  type MacroPhaseId,
} from "../lib/research-workbench";
import { ResearchPhasePath } from "./research-phase-path";

const agentCapabilities = [
  ["demand_validator", "Demand Validator", "implemented"],
  ["research_refiner", "Research Refiner", "planned"],
  ["literature_scout", "Literature Scout", "implemented"],
  ["gap_analyst", "Gap Analyst", "planned"],
  ["idea_generator", "Idea Generator", "implemented"],
  ["experiment_planner", "Experiment Planner", "implemented"],
  ["code_runner", "Code Runner", "planned"],
  ["evidence_auditor", "Evidence Auditor", "planned"],
  ["paper_meeting_writer", "Paper & Meeting Writer", "implemented"],
].map(([agentId, displayName, status]): WorkflowAgentCapability => ({
  agent_id: agentId,
  automation_status: status === "implemented" ? "implemented" : "planned",
  display_name: displayName,
  provider_requirement: status === "implemented" ? "model_provider" : "not_implemented",
  stage_runner_available: status === "implemented",
  status_detail: status === "implemented" ? "Implemented" : "Planned",
  tool_permissions: [],
}));

const stageAgents = [
  ["demand_validator", "Demand Validator", "complete"],
  ["literature_scout", "Literature Scout", "pending"],
  ["idea_generator", "Idea Generator", "pending"],
  ["experiment_planner", "Experiment Planner", "blocked"],
  ["paper_meeting_writer", "Paper & Meeting Writer", "pending"],
].map(([agentId, title, status], index): StageCard => ({
  agent_id: agentId,
  confidence: index === 0 ? "high" : "unknown",
  created_at: "2026-07-10T00:00:00Z",
  evidence_payload: {},
  human_approved: index === 0 ? true : null,
  id: `stage-${index + 1}`,
  input_payload: {},
  output_payload: {},
  quest_id: "quest-1",
  review_notes: "",
  status: status === "complete" ? "complete" : status === "blocked" ? "blocked" : "pending",
  summary: index === 0 ? "Verified demand from two interviews." : "",
  title,
  updated_at: "2026-07-10T00:00:00Z",
}));

const provider: Provider = {
  base_url: "https://model.example.com/v1",
  created_at: "2026-07-10T00:00:00Z",
  default_model: "research-model",
  id: "provider-1",
  is_active: true,
  kind: "openai_compatible",
  name: "Lab Model",
  owner_user_id: null,
  scope: "shared",
  updated_at: "2026-07-10T00:00:00Z",
};

const providerReadinessData: ProviderReadinessData = {
  assignments: [],
  error: null,
  loaded: true,
  loading: false,
  providers: [provider],
};

const phases = buildMacroPhaseViews(stageAgents, agentCapabilities);

function PhasePathHarness({ nextActionPhaseId }: { readonly nextActionPhaseId: MacroPhaseId | null }) {
  const [selectedPhaseId, setSelectedPhaseId] = useState<MacroPhaseId>("demand_scope");

  return (
    <I18nProvider>
      <ResearchPhasePath
        nextAction={null}
        nextActionPhaseId={nextActionPhaseId}
        onSelectPhase={setSelectedPhaseId}
        phases={phases}
        providerReadinessData={providerReadinessData}
        selectedPhaseId={selectedPhaseId}
        stages={stageAgents}
      />
    </I18nProvider>
  );
}

describe("ResearchPhasePath", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    window.localStorage.setItem("noviscope-language", "en");
  });

  it("renders five ordered phase buttons and truthful planned roles", () => {
    render(<PhasePathHarness nextActionPhaseId={null} />);

    const phaseButtons = screen.getAllByRole("button", { name: /phase/i });
    expect(phaseButtons).toHaveLength(5);
    expect(phaseButtons.map((button) => button.getAttribute("aria-label"))).toEqual([
      "Phase 1: Demand scope",
      "Phase 2: Literature gap",
      "Phase 3: Hypothesis framing",
      "Phase 4: Experiment verification",
      "Phase 5: Paper planning",
    ]);
    expect(screen.getByRole("status", { name: "Code Runner: Planned" })).toHaveTextContent(
      "Planned",
    );
    expect(screen.getByRole("status", { name: "Evidence Auditor: Planned" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  it("moves selection and focus with arrow keys", async () => {
    const user = userEvent.setup();
    render(<PhasePathHarness nextActionPhaseId={null} />);

    const firstPhase = screen.getByRole("button", { name: "Phase 1: Demand scope" });
    firstPhase.focus();
    await user.keyboard("{ArrowRight}");

    expect(screen.getByRole("button", { name: "Phase 2: Literature gap" })).toHaveFocus();
    expect(screen.getByRole("button", { name: "Phase 2: Literature gap" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("marks the selected phase and the authoritative action phase independently", () => {
    render(<PhasePathHarness nextActionPhaseId="literature_gap" />);

    expect(screen.getByRole("button", { name: "Phase 1: Demand scope" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(
      within(screen.getByRole("button", { name: "Phase 2: Literature gap" })).getByText(
        "Current action",
      ),
    ).toBeInTheDocument();
  });
});
