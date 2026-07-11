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
      human_demand_reviewed: true,
      human_demand_sources: ["Customer interview"],
      source_policy: "model_only_no_external_source_verification",
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

  it("presents a structured demand conclusion instead of serialized JSON", () => {
    const serializedSummary = JSON.stringify({
      summary: "The worksheet-restoration demand is plausible but still needs customer evidence.",
      demand_assessment: "plausible",
      confidence: "medium",
    });

    renderTabs(stage({
      confidence: "medium",
      output_payload: {
        demand_assessment: "plausible",
        evidence_for_demand: ["A tutoring company reuses completed worksheets."],
        go_or_no_go_recommendation: "go_with_human_review",
        missing_evidence: ["No customer interview has been independently verified."],
        next_step: "Verify the workflow with a customer before planning experiments.",
        real_world_scenario: "Restore completed worksheets for reuse.",
        risks: ["Available data may not represent real classroom handwriting."],
        target_user_or_customer: "Education content providers",
      },
      summary: serializedSummary,
    }));

    expect(screen.getByText("Research conclusion")).toBeInTheDocument();
    expect(screen.getByText(
      "The worksheet-restoration demand is plausible but still needs customer evidence.",
    )).toBeInTheDocument();
    expect(screen.getByText("Continue after human review")).toBeInTheDocument();
    expect(screen.getByText("Restore completed worksheets for reuse.")).toBeInTheDocument();
    expect(screen.getByText("A tutoring company reuses completed worksheets.")).toBeInTheDocument();
    expect(screen.getByText("No customer interview has been independently verified.")).toBeInTheDocument();
    expect(screen.queryByText(serializedSummary)).not.toBeInTheDocument();
    expect(screen.queryByText(/\"demand_assessment\"/)).not.toBeInTheDocument();
  });

  it("does not expose malformed JSON-like summaries", () => {
    const malformedSummary = '{"summary":"Broken serialized model output",';

    renderTabs(stage({
      output_payload: {
        demand_assessment: "plausible",
        go_or_no_go_recommendation: "needs_more_evidence",
      },
      summary: malformedSummary,
    }));

    expect(screen.getByText("No summary yet.")).toBeInTheDocument();
    expect(screen.queryByText(malformedSummary)).not.toBeInTheDocument();
    expect(screen.queryByText(/\{"summary"/)).not.toBeInTheDocument();
  });

  it("does not label unreviewed demand leads as human-reviewed sources", () => {
    renderTabs(stage({
      evidence_payload: {
        human_demand_reviewed: false,
        human_demand_sources: ["Unverified customer lead"],
        source_policy: "model_only_no_external_source_verification",
      },
    }));

    expect(screen.getByText("Source verification: Model output only")).toBeInTheDocument();
    expect(screen.queryByText(/Human-reviewed sources/)).not.toBeInTheDocument();
  });

  it("localizes demand decisions and advanced payload labels for Chinese readers", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem("noviscope-language", "zh");

    renderTabs(stage({
      confidence: "medium",
      output_payload: {
        demand_assessment: "weak",
        go_or_no_go_recommendation: "go_with_human_review",
        next_step: "先核验企业工作流，再进入实验设计。",
        real_world_scenario: "擦除已填写试卷中的手写内容。",
      },
      summary: "需求基本可信，但仍需要企业证据。",
    }));

    expect(screen.getByText("科研结论")).toBeInTheDocument();
    expect(screen.getByText("需求证据较弱")).toBeInTheDocument();
    expect(screen.getByText("人工复核后继续")).toBeInTheDocument();
    expect(screen.getByText("置信度: 中")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "证据" }));
    await user.click(screen.getByText("高级信息"));

    expect(screen.getByText("输入数据")).toBeInTheDocument();
    expect(screen.getByText("输出数据")).toBeInTheDocument();
    expect(screen.getByText("证据数据")).toBeInTheDocument();
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
