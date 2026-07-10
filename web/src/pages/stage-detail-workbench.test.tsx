import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getAgentAssignments } from "../api/agent-assignments";
import { getCurrentUser } from "../api/auth";
import { getProviders } from "../api/providers";
import { getQuest, getQuestStages, runStage } from "../api/quests";
import type {
  Provider,
  Quest,
  StageCard,
  User,
  WorkflowAgentCapability,
  WorkflowNextAction,
} from "../api/types";
import { getWorkflowCapabilities, getWorkflowNextActions } from "../api/workflow";
import { AuthProvider } from "../auth/auth-context";
import { I18nProvider } from "../i18n/i18n-context";
import { StageDetailPage } from "./stage-detail";

vi.mock("../api/agent-assignments", () => ({ getAgentAssignments: vi.fn() }));
vi.mock("../api/auth", () => ({ getCurrentUser: vi.fn(), logoutUser: vi.fn() }));
vi.mock("../api/providers", () => ({ getProviders: vi.fn() }));
vi.mock("../api/quests", () => ({
  getQuest: vi.fn(),
  getQuestStages: vi.fn(),
  runStage: vi.fn(),
  updateStage: vi.fn(),
}));
vi.mock("../api/workflow", () => ({
  getWorkflowCapabilities: vi.fn(),
  getWorkflowNextActions: vi.fn(),
}));

const timestamp = "2026-07-10T00:00:00Z";
const provider: Provider = {
  base_url: "https://model.example.com/v1",
  created_at: timestamp,
  default_model: "research-model",
  id: "provider-1",
  is_active: true,
  kind: "anthropic",
  name: "Lab Model",
  owner_user_id: null,
  scope: "shared",
  updated_at: timestamp,
};
const quest: Quest = {
  created_at: timestamp,
  id: "quest-1",
  initial_direction: "Restore document structure.",
  owner_user_id: "user-1",
  status: "draft",
  title: "Reliable restoration",
  updated_at: timestamp,
};
const user: User = {
  created_at: timestamp,
  display_name: "Researcher",
  email: "researcher@example.com",
  id: "user-1",
  is_active: true,
  role: "member",
  updated_at: timestamp,
};
const stage: StageCard = {
  agent_id: "idea_generator",
  confidence: "unknown",
  created_at: timestamp,
  evidence_payload: {},
  human_approved: null,
  id: "stage-1",
  input_payload: {},
  output_payload: {},
  quest_id: quest.id,
  review_notes: "",
  status: "pending",
  summary: "",
  title: "Idea Generator",
  updated_at: timestamp,
};
const secondStage: StageCard = {
  ...stage,
  id: "stage-2",
  title: "Second stage",
};
const nextAction: WorkflowNextAction = {
  action_type: "run_stage",
  agent_id: stage.agent_id,
  blocking_reason: "",
  can_run: true,
  detail: "Ready to run.",
  label: "Run stage",
  priority: 1,
  stage_id: stage.id,
  stage_status: stage.status,
  stage_title: stage.title,
};
const capability: WorkflowAgentCapability = {
  agent_id: stage.agent_id,
  automation_status: "implemented",
  display_name: stage.title,
  provider_requirement: "model_provider",
  stage_runner_available: true,
  status_detail: "Runnable with a provider.",
  tool_permissions: [],
};

type Deferred<Value> = {
  readonly promise: Promise<Value>;
  readonly resolve: (value: Value) => void;
};

function deferred<Value>(): Deferred<Value> {
  let resolve: (value: Value) => void = (_value) => undefined;
  const promise = new Promise<Value>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

function NavigateToSecondStage() {
  const navigate = useNavigate();
  return (
    <button onClick={() => navigate("/stages/stage-2?quest=quest-1")} type="button">
      Navigate to second stage
    </button>
  );
}

describe("StageDetailPage shared workbench", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.setItem("noviscope-language", "en");
    vi.mocked(getAgentAssignments).mockResolvedValue([]);
    vi.mocked(getCurrentUser).mockResolvedValue(user);
    vi.mocked(getProviders).mockResolvedValue([provider]);
    vi.mocked(getQuest).mockResolvedValue(quest);
    vi.mocked(getQuestStages).mockResolvedValue([stage]);
    vi.mocked(getWorkflowCapabilities).mockResolvedValue([capability]);
    vi.mocked(getWorkflowNextActions).mockResolvedValue({
      action_count: 1,
      actions: [nextAction],
      quest_id: quest.id,
    });
  });

  it("orders authoritative action before full tabs and loads capability truth", async () => {
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

    const heading = await screen.findByRole("heading", { name: "Next action" });
    const tablist = screen.getByRole("tablist", { name: "Stage workbench" });

    expect(heading.compareDocumentPosition(tablist) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
    expect(screen.getByRole("combobox", { name: "Provider override" })).toBeInTheDocument();
    expect(screen.getByText("Advanced editor").closest("details")).not.toHaveAttribute("open");
    expect(screen.getByRole("button", { name: "Download review packet" })).toBeInTheDocument();
    expect(getWorkflowCapabilities).toHaveBeenCalledOnce();
  });

  it("does not refresh or show run success for a stage left during a delayed run", async () => {
    const pendingRun = deferred<StageCard>();
    vi.mocked(runStage).mockReturnValue(pendingRun.promise);
    vi.mocked(getQuestStages).mockResolvedValue([stage, secondStage]);
    const userEvents = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/stages/stage-1?quest=quest-1"]}>
        <AuthProvider>
          <I18nProvider>
            <Routes>
              <Route
                element={
                  <>
                    <StageDetailPage />
                    <NavigateToSecondStage />
                  </>
                }
                path="/stages/:stageId"
              />
            </Routes>
          </I18nProvider>
        </AuthProvider>
      </MemoryRouter>,
    );
    await screen.findByRole("heading", { level: 1, name: stage.title });
    await userEvents.click(screen.getByRole("button", { name: "Run agent" }));
    await userEvents.click(screen.getByRole("button", { name: "Navigate to second stage" }));
    await screen.findByRole("heading", { level: 1, name: secondStage.title });

    await act(async () => {
      pendingRun.resolve({ ...stage, status: "complete" });
      await pendingRun.promise;
    });

    await waitFor(() => expect(getQuestStages).toHaveBeenCalledTimes(2));
    expect(screen.queryByText("Stage run completed")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: secondStage.title })).toBeInTheDocument();
  });
});
