import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getAgentAssignments } from "../api/agent-assignments";
import { getCurrentUser } from "../api/auth";
import { getProviders } from "../api/providers";
import {
  getQuest,
  getQuestStages,
  getStageArtifacts,
  updateStage,
} from "../api/quests";
import type {
  Provider,
  Quest,
  StageCard,
  User,
  WorkflowNextAction,
} from "../api/types";
import { getWorkflowNextActions } from "../api/workflow";
import { AuthProvider } from "../auth/auth-context";
import { I18nProvider } from "../i18n/i18n-context";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import { StageDetailPage } from "../pages/stage-detail";
import { StageWorkbenchTabs } from "./stage-workbench-tabs";

vi.mock("../api/agent-assignments", () => ({ getAgentAssignments: vi.fn() }));
vi.mock("../api/auth", () => ({ getCurrentUser: vi.fn(), logoutUser: vi.fn() }));
vi.mock("../api/providers", () => ({ getProviders: vi.fn() }));
vi.mock("../api/quests", () => ({
  buildStageArtifactDownloadPath: (downloadUrl: string) => `/api${downloadUrl}`,
  getQuest: vi.fn(),
  getQuestStages: vi.fn(),
  getStageArtifacts: vi.fn(),
  runStage: vi.fn(),
  updateStage: vi.fn(),
}));
vi.mock("../api/workflow", () => ({ getWorkflowNextActions: vi.fn() }));

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

const quest: Quest = {
  created_at: "2026-07-10T00:00:00Z",
  id: "quest-1",
  initial_direction: "Restore document structure without inventing evidence.",
  owner_user_id: "user-1",
  status: "demand_review",
  title: "Reliable document restoration",
  updated_at: "2026-07-10T00:00:00Z",
};

const user: User = {
  created_at: "2026-07-10T00:00:00Z",
  display_name: "Researcher",
  email: "researcher@example.com",
  id: "user-1",
  is_active: true,
  role: "member",
  updated_at: "2026-07-10T00:00:00Z",
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
) {
  return render(
    <MemoryRouter>
      <I18nProvider>
        <StageWorkbenchTabs
          mode={mode}
          onRunStage={onRunStage}
          onStageChange={onStageChange}
          providerReadinessData={providerReadinessData}
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
    vi.clearAllMocks();
    window.localStorage.setItem("noviscope-language", "en");
    vi.mocked(getAgentAssignments).mockResolvedValue([]);
    vi.mocked(getCurrentUser).mockResolvedValue(user);
    vi.mocked(getProviders).mockResolvedValue([provider]);
    vi.mocked(getStageArtifacts).mockResolvedValue({
      artifacts: [],
      stage_id: "stage-1",
    });
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
    await user.click(screen.getByRole("button", { name: "Run stage" }));

    expect(onRunStage).toHaveBeenCalledWith("stage-1", undefined);
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

  it("keeps full review controls editable and reports review mutations", async () => {
    const user = userEvent.setup();
    const onStageChange = vi.fn();
    const reviewedStage = stage({ human_approved: true });
    vi.mocked(updateStage).mockResolvedValue(reviewedStage);
    renderTabs(stage(), vi.fn(), "full", onStageChange);

    await user.click(screen.getByRole("tab", { name: "Review" }));
    await user.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => expect(onStageChange).toHaveBeenCalledWith(reviewedStage));
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset to pending" })).toBeInTheDocument();
  });

  it("keeps complete output controls available in full Artifacts mode", async () => {
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
      vi.fn(),
      "full",
    );

    await user.click(screen.getByRole("tab", { name: "Artifacts" }));

    expect(
      screen.getByRole("button", { name: "Select for experiment design" }),
    ).toBeInTheDocument();
  });

  it("keeps artifact download actions available in full Artifacts mode", async () => {
    const user = userEvent.setup();
    vi.mocked(getStageArtifacts).mockResolvedValue({
      artifacts: [
        {
          available: true,
          download_url: "/stages/stage-1/artifacts/chinese_research_brief_markdown",
          filename: "chinese-research-brief.md",
          key: "chinese_research_brief_markdown",
          media_type: "text/markdown",
          missing_reason: "",
          title: "Chinese research brief",
        },
      ],
      stage_id: "stage-1",
    });
    renderTabs(
      stage({
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
      }),
      vi.fn(),
      "full",
    );

    await user.click(screen.getByRole("tab", { name: "Artifacts" }));

    expect(await screen.findByRole("link", { name: "Download Markdown" })).toHaveAttribute(
      "href",
      "/api/stages/stage-1/artifacts/chinese_research_brief_markdown",
    );
  });

  it("renders the authoritative next action before full tabs and keeps Advanced closed", async () => {
    const currentStage = stage();
    const nextStage = stage({
      agent_id: "literature_scout",
      evidence_payload: {},
      human_approved: null,
      id: "stage-2",
      output_payload: {},
      status: "pending",
      summary: "",
      title: "Literature Scout",
    });
    const nextAction: WorkflowNextAction = {
      action_type: "review_stage",
      agent_id: currentStage.agent_id,
      blocking_reason: "human_review_required",
      can_run: false,
      detail: "Review the stored demand evidence.",
      label: "Review demand evidence",
      priority: 1,
      stage_id: currentStage.id,
      stage_status: currentStage.status,
      stage_title: currentStage.title,
    };
    vi.mocked(getQuest).mockResolvedValue(quest);
    vi.mocked(getQuestStages).mockResolvedValue([currentStage, nextStage]);
    vi.mocked(getWorkflowNextActions).mockResolvedValue({
      action_count: 1,
      actions: [nextAction],
      quest_id: quest.id,
    });

    render(
      <MemoryRouter initialEntries={["/stages/stage-1?quest=quest-1"]}>
        <AuthProvider>
          <I18nProvider>
            <Routes>
              <Route element={<StageDetailPage />} path="/stages/:stageId" />
            </Routes>
          </I18nProvider>
        </AuthProvider>
      </MemoryRouter>,
    );

    const nextActionHeading = await screen.findByRole("heading", { name: "Next action" });
    const tablist = screen.getByRole("tablist", { name: "Stage workbench" });

    expect(
      nextActionHeading.compareDocumentPosition(tablist) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).not.toBe(0);
    expect(screen.getByText("Advanced editor").closest("details")).not.toHaveAttribute("open");
    expect(screen.getByRole("button", { name: "Download review packet" })).toBeInTheDocument();
  });
});
