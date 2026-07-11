import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getStageArtifacts, updateStage } from "../api/quests";
import type { Provider, StageCard } from "../api/types";
import { I18nProvider } from "../i18n/i18n-context";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import { StageWorkbenchTabs } from "./stage-workbench-tabs";

vi.mock("../api/quests", () => ({
  buildStageArtifactDownloadPath: (downloadUrl: string) => `/api${downloadUrl}`,
  getStageArtifacts: vi.fn(),
  updateStage: vi.fn(),
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

const readiness: ProviderReadinessData = {
  assignments: [],
  error: null,
  loaded: true,
  loading: false,
  providers: [provider],
};

function stage(overrides: Partial<StageCard> = {}): StageCard {
  return {
    agent_id: "demand_validator",
    confidence: "high",
    created_at: "2026-07-10T00:00:00Z",
    evidence_payload: { human_demand_sources: ["Customer interview"] },
    human_approved: null,
    id: "stage-1",
    input_payload: { research_direction: "Reliable document restoration" },
    output_payload: { demand_assessment: "plausible" },
    quest_id: "quest-1",
    review_notes: "Review dataset ownership.",
    status: "complete",
    summary: "Demand evidence is ready for review.",
    title: "Demand Validator",
    updated_at: "2026-07-10T00:00:00Z",
    ...overrides,
  };
}

function renderFull(
  currentStage: StageCard,
  onStageChange = vi.fn(),
  providerReadinessData = readiness,
) {
  return render(
    <MemoryRouter>
      <I18nProvider>
        <StageWorkbenchTabs
          currentUserId="user-1"
          mode="full"
          onRunStage={vi.fn()}
          onStageChange={onStageChange}
          providerReadinessData={providerReadinessData}
          runningStageId={null}
          stage={currentStage}
          stages={[currentStage]}
        />
      </I18nProvider>
    </MemoryRouter>,
  );
}

function RefreshingStageHarness() {
  const [currentStage, setCurrentStage] = useState(stage());
  return (
    <MemoryRouter>
      <I18nProvider>
        <StageWorkbenchTabs
          currentUserId="user-1"
          mode="full"
          onRunStage={vi.fn()}
          onStageChange={setCurrentStage}
          providerReadinessData={readiness}
          runningStageId={null}
          stage={currentStage}
          stages={[currentStage]}
        />
      </I18nProvider>
    </MemoryRouter>
  );
}

describe("StageWorkbenchTabs full mode", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.setItem("noviscope-language", "en");
    vi.mocked(getStageArtifacts).mockResolvedValue({ artifacts: [], stage_id: "stage-1" });
  });

  it("keeps review controls editable and reports review mutations", async () => {
    const user = userEvent.setup();
    const onStageChange = vi.fn();
    const reviewedStage = stage({ human_approved: true });
    vi.mocked(updateStage).mockResolvedValue(reviewedStage);
    renderFull(stage(), onStageChange);

    await user.click(screen.getByRole("tab", { name: "Review" }));
    await user.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => expect(onStageChange).toHaveBeenCalledWith(reviewedStage));
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset to pending" })).toBeInTheDocument();
  });

  it("keeps the active tab when a mutation refreshes the same stage", async () => {
    const user = userEvent.setup();
    vi.mocked(updateStage).mockResolvedValue(stage({ human_approved: true }));
    render(<RefreshingStageHarness />);

    await user.click(screen.getByRole("tab", { name: "Review" }));
    await user.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Review" })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });
  });

  it("keeps complete output controls available in Artifacts", async () => {
    const user = userEvent.setup();
    renderFull(stage({
      agent_id: "idea_generator",
      output_payload: {
        gaps: [],
        ideas: [{
          application_value: "high",
          based_on_which_papers: ["Paper A"],
          confidence: "high",
          core_hypothesis: "Structure constraints preserve layout.",
          expected_improvement: "Higher OCR recovery.",
          experiment_feasibility: "high",
          idea_id: "idea-1",
          idea_title: "Structure-aware restoration",
          novelty_risk: "medium",
          required_baseline: "Inpainting baseline",
          required_data: "Paired worksheet scans",
        }],
        selection_status: "pending_human_selection",
        selected_idea_ids: [],
        summary: "One experiment-ready idea.",
      },
      title: "Idea Generator",
    }));

    await user.click(screen.getByRole("tab", { name: "Artifacts" }));

    expect(screen.getByRole("button", { name: "Select for experiment design" })).toBeInTheDocument();
  });

  it("marks saved demand evidence as human reviewed", async () => {
    const user = userEvent.setup();
    const reviewedStage = stage({
      evidence_payload: {
        human_demand_reviewed: true,
        human_demand_sources: ["Customer interview"],
        human_demand_verdict: "verified",
      },
    });
    vi.mocked(updateStage).mockResolvedValue(reviewedStage);
    renderFull(stage());

    await user.click(screen.getByRole("tab", { name: "Artifacts" }));
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Demand evidence verdict" }),
      "verified",
    );
    await user.click(screen.getByRole("button", { name: "Save demand evidence" }));

    await waitFor(() => {
      expect(updateStage).toHaveBeenCalledWith(
        "stage-1",
        expect.objectContaining({
          evidence_payload: expect.objectContaining({
            human_demand_reviewed: true,
            human_demand_sources: ["Customer interview"],
            human_demand_verdict: "verified",
          }),
        }),
      );
    });
  });

  it("keeps shared Anthropic ready as the default while only personal Anthropic is selectable", async () => {
    const user = userEvent.setup();
    const anthropicProvider: Provider = {
      ...provider,
      default_model: "claude-research",
      id: "provider-anthropic",
      kind: "anthropic",
      name: "Anthropic Lab",
    };
    const personalAnthropicProvider: Provider = {
      ...anthropicProvider,
      id: "provider-personal-anthropic",
      name: "Personal Anthropic",
      owner_user_id: "user-1",
      scope: "personal",
    };
    renderFull(stage({ status: "pending" }), vi.fn(), {
      ...readiness,
      providers: [anthropicProvider, personalAnthropicProvider],
    });

    await user.click(screen.getByRole("tab", { name: "Run" }));

    expect(screen.getByText("Provider ready")).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Anthropic Lab" })).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Personal Anthropic" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run stage" })).toBeEnabled();
  });

  it("keeps artifact download actions available in Artifacts", async () => {
    const user = userEvent.setup();
    vi.mocked(getStageArtifacts).mockResolvedValue({
      artifacts: [{
        available: true,
        download_url: "/stages/stage-1/artifacts/chinese_research_brief_markdown",
        filename: "chinese-research-brief.md",
        key: "chinese_research_brief_markdown",
        media_type: "text/markdown",
        missing_reason: "",
        title: "Chinese research brief",
      }],
      stage_id: "stage-1",
    });
    renderFull(stage({
      agent_id: "paper_meeting_writer",
      output_payload: {
        chinese_research_brief_markdown: "# Chinese brief",
        confidence: "medium",
        english_research_brief_markdown: "# English brief",
        experiment_results_not_available: ["No verified metrics."],
        human_review_required: ["Review all claims."],
        ieee_paper_skeleton_markdown: "# Paper skeleton",
        meeting_outline_markdown: "# Meeting outline",
        model_generated_hypotheses: ["Structure may improve recovery."],
        summary: "Draft artifacts are ready for review.",
        verified_facts: ["Demand evidence was reviewed."],
        warnings: [],
      },
      title: "Paper and Meeting Writer",
    }));

    await user.click(screen.getByRole("tab", { name: "Artifacts" }));

    expect(await screen.findByRole("link", { name: "Download Markdown" })).toHaveAttribute(
      "href",
      "/api/stages/stage-1/artifacts/chinese_research_brief_markdown",
    );
  });

  it("includes paper artifacts in the human Review tab", async () => {
    renderFull(stage({ agent_id: "paper_meeting_writer", title: "Paper and Meeting Writer" }));

    expect(screen.getByRole("tab", { name: "Review" })).toBeInTheDocument();
  });
});
