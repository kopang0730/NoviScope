import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Provider, StageCard } from "../api/types";
import { I18nProvider } from "../i18n/i18n-context";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import { StageWorkbenchTabs } from "./stage-workbench-tabs";

const personalProvider: Provider = {
  base_url: "https://personal.example.com/v1",
  created_at: "2026-07-10T00:00:00Z",
  default_model: "personal-model",
  id: "personal-provider",
  is_active: true,
  kind: "openai_compatible",
  name: "Personal Lab Model",
  owner_user_id: "user-1",
  scope: "personal",
  updated_at: "2026-07-10T00:00:00Z",
};

const otherUserProvider: Provider = {
  ...personalProvider,
  id: "other-user-provider",
  name: "Other User Model",
  owner_user_id: "user-2",
};

const sharedProvider: Provider = {
  base_url: "https://model.example.com/v1",
  created_at: "2026-07-10T00:00:00Z",
  default_model: "research-model",
  id: "shared-provider",
  is_active: true,
  kind: "openai_compatible",
  name: "Shared Lab Model",
  owner_user_id: null,
  scope: "shared",
  updated_at: "2026-07-10T00:00:00Z",
};

const providerReadinessData: ProviderReadinessData = {
  assignments: [],
  error: null,
  loaded: true,
  loading: false,
  providers: [sharedProvider, personalProvider, otherUserProvider],
};

function stage(overrides: Partial<StageCard> = {}): StageCard {
  return {
    agent_id: "demand_validator",
    confidence: "high",
    created_at: "2026-07-10T00:00:00Z",
    evidence_payload: {
      human_demand_sources: ["Customer interview"],
      source_policy: "human_reviewed_sources",
    },
    human_approved: null,
    id: "stage-1",
    input_payload: { research_direction: "Reliable document restoration" },
    output_payload: {
      demand_assessment: "plausible",
      real_world_scenario: "Education teams reuse marked worksheets.",
    },
    quest_id: "quest-1",
    review_notes: "Review dataset ownership.",
    status: "complete",
    summary: "Demand evidence is ready for review.",
    title: "Demand Validator",
    updated_at: "2026-07-10T00:00:00Z",
    ...overrides,
  };
}

function renderTabs(
  currentStage: StageCard,
  onRunStage = vi.fn(),
  mode: "compact" | "full" = "compact",
  onStageChange = vi.fn(),
  readinessData = providerReadinessData,
  runningStageId: string | null = null,
) {
  return render(
    <MemoryRouter>
      <I18nProvider>
        <StageWorkbenchTabs
          currentUserId="user-1"
          mode={mode}
          onRunStage={onRunStage}
          onStageChange={onStageChange}
          providerReadinessData={readinessData}
          runningStageId={runningStageId}
          stage={currentStage}
          stages={[currentStage]}
        />
      </I18nProvider>
    </MemoryRouter>,
  );
}

describe("StageWorkbenchTabs", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    window.localStorage.setItem("noviscope-language", "en");
  });

  it("shows only meaningful tabs for an implemented review and output stage", () => {
    renderTabs(stage());

    expect(screen.getByRole("tab", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Evidence" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Run" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Review" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Artifacts" })).toBeInTheDocument();
  });

  it("keeps unavailable tabs out of a planned stage inspector", () => {
    renderTabs(
      stage({
        agent_id: "code_runner",
        evidence_payload: {},
        output_payload: {},
        status: "pending",
        summary: "",
        title: "Code Runner",
      }),
    );

    expect(screen.getAllByRole("tab")).toHaveLength(1);
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("tab", { name: "Evidence" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Run" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Review" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Artifacts" })).not.toBeInTheDocument();
  });

  it("renders only the active tabpanel and keeps Advanced closed", async () => {
    const user = userEvent.setup();
    renderTabs(stage());

    expect(screen.getAllByRole("tabpanel")).toHaveLength(1);
    expect(screen.getByRole("tabpanel", { name: "Overview" })).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Evidence" }));

    expect(screen.getAllByRole("tabpanel")).toHaveLength(1);
    expect(screen.getByRole("tabpanel", { name: "Evidence" })).toBeInTheDocument();
    expect(screen.queryByRole("tabpanel", { name: "Overview" })).not.toBeInTheDocument();
    expect(screen.getByText("Advanced").closest("details")).not.toHaveAttribute("open");
  });

  it("runs the selected implemented stage from the Run panel", async () => {
    const user = userEvent.setup();
    const onRunStage = vi.fn();
    renderTabs(stage({ status: "pending" }), onRunStage);

    await user.click(screen.getByRole("tab", { name: "Run" }));
    expect(screen.getByRole("option", { name: "Personal Lab Model" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Other User Model" })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Shared Lab Model" })).not.toBeInTheDocument();
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Provider override" }),
      "personal-provider",
    );
    await user.click(screen.getByRole("button", { name: "Run stage" }));

    expect(onRunStage).toHaveBeenCalledWith("stage-1", "personal-provider");
  });

  it("allows an owned personal override when the shared default is inactive", async () => {
    const user = userEvent.setup();
    const inactiveSharedProvider = { ...sharedProvider, is_active: false };
    renderTabs(
      stage({ status: "pending" }),
      vi.fn(),
      "compact",
      vi.fn(),
      {
        ...providerReadinessData,
        assignments: [{
          agent_id: "demand_validator",
          display_name: "Demand Validator",
          effective_model: "research-model",
          model_name: null,
          provider_id: inactiveSharedProvider.id,
          provider_is_active: false,
          provider_kind: inactiveSharedProvider.kind,
          provider_name: inactiveSharedProvider.name,
        }],
        providers: [inactiveSharedProvider, personalProvider],
      },
    );

    await user.click(screen.getByRole("tab", { name: "Run" }));
    expect(screen.getByRole("button", { name: "Run stage" })).toBeDisabled();
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Provider override" }),
      personalProvider.id,
    );

    expect(screen.getByRole("button", { name: "Run stage" })).toBeEnabled();
  });

  it("disables the Run panel action while the stage is already in flight", async () => {
    const user = userEvent.setup();
    renderTabs(stage({ status: "pending" }), vi.fn(), "compact", vi.fn(), providerReadinessData, "stage-1");

    await user.click(screen.getByRole("tab", { name: "Run" }));

    expect(screen.getByRole("button", { name: "Working..." })).toBeDisabled();
  });

  it("keeps compact Artifacts read-only and links to Stage Detail", async () => {
    const user = userEvent.setup();
    renderTabs(
      stage({
        agent_id: "idea_generator",
        output_payload: {
          gaps: [],
          ideas: [
            {
              application_value: "high",
              based_on_which_papers: ["Paper A"],
              confidence: "high",
              core_hypothesis: "A constrained model preserves document structure.",
              expected_improvement: "Higher OCR recovery.",
              experiment_feasibility: "high",
              idea_id: "idea-1",
              idea_title: "Structure-aware restoration",
              novelty_risk: "medium",
              required_baseline: "Inpainting baseline",
              required_data: "Paired worksheet scans",
            },
          ],
          selection_status: "pending_human_selection",
          selected_idea_ids: [],
          summary: "One experiment-ready idea.",
        },
        title: "Idea Generator",
      }),
    );

    await user.click(screen.getByRole("tab", { name: "Artifacts" }));

    expect(
      screen.queryByRole("button", { name: "Select for experiment design" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Stage Detail" })).toHaveAttribute(
      "href",
      "/stages/stage-1?quest=quest-1",
    );
  });

  it("deep-links the compact Review handoff to the full Review tab", async () => {
    const user = userEvent.setup();
    renderTabs(stage());

    await user.click(screen.getByRole("tab", { name: "Review" }));

    expect(screen.getByRole("link", { name: "Open Stage Detail" })).toHaveAttribute(
      "href",
      "/stages/stage-1?quest=quest-1#review",
    );
  });

});
