import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type {
  Provider,
  ProviderRequirement,
  WorkflowAgentCapability,
  WorkflowNextAction,
} from "../api/types";
import { I18nProvider } from "../i18n/i18n-context";
import { StageNextActionCard } from "./stage-next-action-card";

const action: WorkflowNextAction = {
  action_type: "run_stage",
  agent_id: "idea_generator",
  blocking_reason: "",
  can_run: true,
  detail: "Ready to run.",
  label: "Run idea generation",
  priority: 1,
  stage_id: "stage-1",
  stage_status: "pending",
  stage_title: "Idea Generator",
};

const providers: readonly Provider[] = [
  {
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
  },
  {
    base_url: "https://shared.example.com/v1",
    created_at: "2026-07-10T00:00:00Z",
    default_model: "shared-model",
    id: "shared-provider",
    is_active: true,
    kind: "anthropic",
    name: "Shared Anthropic Model",
    owner_user_id: null,
    scope: "shared",
    updated_at: "2026-07-10T00:00:00Z",
  },
  {
    base_url: "https://personal-anthropic.example.com/v1",
    created_at: "2026-07-10T00:00:00Z",
    default_model: "claude-sonnet",
    id: "personal-anthropic",
    is_active: true,
    kind: "anthropic",
    name: "Personal Anthropic Model",
    owner_user_id: "user-1",
    scope: "personal",
    updated_at: "2026-07-10T00:00:00Z",
  },
  {
    base_url: "https://inactive.example.com/v1",
    created_at: "2026-07-10T00:00:00Z",
    default_model: "inactive-model",
    id: "inactive-provider",
    is_active: false,
    kind: "custom",
    name: "Inactive Model",
    owner_user_id: "user-1",
    scope: "personal",
    updated_at: "2026-07-10T00:00:00Z",
  },
];

function capability(
  providerRequirement: ProviderRequirement,
  stageRunnerAvailable = true,
): WorkflowAgentCapability {
  return {
    agent_id: action.agent_id,
    automation_status: "implemented",
    display_name: action.stage_title,
    provider_requirement: providerRequirement,
    stage_runner_available: stageRunnerAvailable,
    status_detail: "Capability truth",
    tool_permissions: [],
  };
}

function renderCard(
  workflowCapability: WorkflowAgentCapability,
  onRun: (stageId: string, providerId?: string) => void = vi.fn(),
) {
  return render(
    <I18nProvider>
      <StageNextActionCard
        action={action}
        capabilities={[workflowCapability]}
        currentUserId="user-1"
        onNavigate={vi.fn()}
        onRun={onRun}
        providers={providers}
        questId="quest-1"
        runningStageId={null}
      />
    </I18nProvider>,
  );
}

describe("StageNextActionCard provider override", () => {
  afterEach(cleanup);

  beforeEach(() => {
    window.localStorage.setItem("noviscope-language", "en");
  });

  it.each([
    ["server-managed", capability("server_managed")],
    ["missing runner", capability("model_provider", false)],
  ])("hides the selector for %s actions", (_, workflowCapability) => {
    renderCard(workflowCapability);

    expect(screen.queryByRole("combobox", { name: "Provider override" })).not.toBeInTheDocument();
  });

  it("includes only active personal providers when applicable", () => {
    renderCard(capability("model_provider"));

    expect(screen.getByRole("option", { name: /Personal Lab Model.*Personal/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Personal Anthropic Model.*Personal/i })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Shared Anthropic Model/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Inactive Model/i })).not.toBeInTheDocument();
  });

  it("forwards the selected provider ID when running", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    renderCard(capability("model_provider"), onRun);

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Provider override" }),
      "personal-anthropic",
    );
    await user.click(screen.getByRole("button", { name: "Run agent" }));

    expect(onRun).toHaveBeenCalledWith("stage-1", "personal-anthropic");
  });
});
