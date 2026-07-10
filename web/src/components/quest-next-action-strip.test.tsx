import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type {
  Provider,
  WorkflowActionType,
  WorkflowAgentCapability,
  WorkflowNextAction,
} from "../api/types";
import { I18nProvider } from "../i18n/i18n-context";
import { QuestNextActionStrip } from "./quest-next-action-strip";

function action(actionType: WorkflowActionType): WorkflowNextAction {
  return {
    action_type: actionType,
    agent_id: "literature_scout",
    blocking_reason:
      actionType === "review_stage"
        ? "human_review_required"
        : actionType === "configure_provider"
          ? "missing_provider"
          : actionType === "wait_for_stage"
            ? "stage_already_running"
            : "",
    can_run: actionType === "run_stage",
    detail: "Inspect the stored stage evidence.",
    label: "Backend action label",
    priority: 1,
    stage_id: "stage-1",
    stage_status: actionType === "wait_for_stage" ? "running" : "pending",
    stage_title: "Literature Scout",
  };
}

const capability: WorkflowAgentCapability = {
  agent_id: "literature_scout",
  automation_status: "implemented",
  display_name: "Literature Scout",
  provider_requirement: "model_provider",
  stage_runner_available: true,
  status_detail: "Runnable with a model provider.",
  tool_permissions: ["openalex_search"],
};

const providers: readonly Provider[] = [
  {
    id: "personal-provider",
    name: "Personal Lab Model",
    kind: "openai_compatible",
    scope: "personal",
    owner_user_id: "user-1",
    base_url: "https://personal.example.com/v1",
    default_model: "personal-model",
    is_active: true,
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z",
  },
  {
    id: "shared-provider",
    name: "Shared Lab Model",
    kind: "anthropic",
    scope: "shared",
    owner_user_id: null,
    base_url: "https://shared.example.com/v1",
    default_model: "shared-model",
    is_active: true,
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z",
  },
  {
    id: "personal-anthropic",
    name: "Personal Anthropic Model",
    kind: "anthropic",
    scope: "personal",
    owner_user_id: "user-1",
    base_url: "https://personal-anthropic.example.com/v1",
    default_model: "claude-sonnet",
    is_active: true,
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z",
  },
  {
    id: "inactive-personal-provider",
    name: "Inactive Personal Model",
    kind: "openai_compatible",
    scope: "personal",
    owner_user_id: "user-1",
    base_url: "https://inactive.example.com/v1",
    default_model: "inactive-model",
    is_active: false,
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z",
  },
];

function renderStrip(
  actions: readonly WorkflowNextAction[],
  onRun: (stageId: string, providerId?: string) => void = vi.fn(),
) {
  return render(
    <MemoryRouter>
      <I18nProvider>
        <QuestNextActionStrip
          actions={actions}
          capabilities={[capability]}
          currentUserId="user-1"
          onRun={onRun}
          providers={providers}
          questId="quest-1"
          runningStageId={null}
        />
      </I18nProvider>
    </MemoryRouter>,
  );
}

describe("QuestNextActionStrip", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    window.localStorage.setItem("noviscope-language", "en");
  });

  it("renders exactly one next-action heading", () => {
    renderStrip([action("run_stage")]);

    expect(screen.getAllByRole("heading", { name: "Next action" })).toHaveLength(1);
  });

  it("runs a model-provider stage with only active personal providers as explicit overrides", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    renderStrip([action("run_stage")], onRun);

    const providerSelect = screen.getByRole("combobox", { name: "Provider override" });
    expect(screen.getByRole("option", { name: /Personal Lab Model.*Personal/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Personal Anthropic Model.*Personal/i })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Inactive Personal Model/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Shared Lab Model/i })).not.toBeInTheDocument();

    await user.selectOptions(providerSelect, "personal-anthropic");
    await user.click(screen.getByRole("button", { name: "Run agent" }));

    expect(onRun).toHaveBeenCalledWith("stage-1", "personal-anthropic");
  });

  it("links review actions to the authoritative stage detail", () => {
    renderStrip([action("review_stage")]);

    expect(screen.getByRole("link", { name: "Human review" })).toHaveAttribute(
      "href",
      "/stages/stage-1?quest=quest-1#review",
    );
  });

  it("links provider blockers to provider configuration", () => {
    renderStrip([action("configure_provider")]);

    expect(screen.getByRole("link", { name: "Configure provider" })).toHaveAttribute(
      "href",
      "/providers",
    );
  });

  it("links workflow blockers to the Artifacts tab that can resolve them", () => {
    renderStrip([{
      ...action("resolve_blocker"),
      blocking_reason: "missing_experiment_inputs",
    }]);

    expect(screen.getByRole("link", { name: "Resolve blocker" })).toHaveAttribute(
      "href",
      "/stages/stage-1?quest=quest-1#artifacts",
    );
  });

  it("does not expose an enabled primary command while waiting", () => {
    renderStrip([action("wait_for_stage")]);

    expect(screen.getByRole("button", { name: "Wait for stage" })).toBeDisabled();
  });

  it("renders the no-pending-action state for an empty authoritative response", () => {
    renderStrip([]);

    expect(screen.getByText("No pending action")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
