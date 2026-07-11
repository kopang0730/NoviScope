import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getAgentAssignments } from "../api/agent-assignments";
import { getCurrentUser } from "../api/auth";
import { getProviders } from "../api/providers";
import { getQuest, getQuestStages, getQuests, runStage } from "../api/quests";
import type { Quest, StageCard, User, WorkflowNextActionsResponse } from "../api/types";
import {
  getWorkflowCapabilities,
  getWorkflowCanvasTemplate,
  getWorkflowNextActions,
} from "../api/workflow";
import { AuthProvider } from "../auth/auth-context";
import { I18nProvider } from "../i18n/i18n-context";
import { CanvasWorkspacePage } from "./canvas-workspace";

vi.mock("../api/agent-assignments", () => ({ getAgentAssignments: vi.fn() }));
vi.mock("../api/auth", () => ({ getCurrentUser: vi.fn(), logoutUser: vi.fn() }));
vi.mock("../api/providers", () => ({ getProviders: vi.fn() }));
vi.mock("../api/quests", () => ({
  getQuest: vi.fn(),
  getQuestStages: vi.fn(),
  getQuests: vi.fn(),
  runStage: vi.fn(),
}));
vi.mock("../api/workflow", () => ({
  getWorkflowCapabilities: vi.fn(),
  getWorkflowCanvasTemplate: vi.fn(),
  getWorkflowNextActions: vi.fn(),
}));

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

const timestamp = "2026-07-10T00:00:00Z";
const user: User = {
  created_at: timestamp,
  display_name: "Researcher",
  email: "researcher@example.com",
  id: "user-1",
  is_active: true,
  role: "member",
  updated_at: timestamp,
};

function quest(id: string): Quest {
  return {
    created_at: timestamp,
    id,
    initial_direction: `Direction for ${id}`,
    owner_user_id: user.id,
    status: "draft",
    title: `Quest ${id}`,
    updated_at: timestamp,
  };
}

function stage(questId: string): StageCard {
  return {
    agent_id: "demand_validator",
    confidence: "unknown",
    created_at: timestamp,
    evidence_payload: {},
    human_approved: null,
    id: `stage-${questId}`,
    input_payload: {},
    output_payload: {},
    quest_id: questId,
    review_notes: "",
    status: "pending",
    summary: "",
    title: `Stage ${questId}`,
    updated_at: timestamp,
  };
}

function nextActions(questId: string): WorkflowNextActionsResponse {
  const currentStage = stage(questId);
  return {
    action_count: 1,
    actions: [{
      action_type: "run_stage",
      agent_id: currentStage.agent_id,
      blocking_reason: "",
      can_run: true,
      detail: `Run ${questId}`,
      label: `Run ${questId}`,
      priority: 1,
      stage_id: currentStage.id,
      stage_status: currentStage.status,
      stage_title: currentStage.title,
    }],
    quest_id: questId,
  };
}

describe("CanvasWorkspacePage selection safety", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.setItem("noviscope-language", "en");
    vi.mocked(getAgentAssignments).mockResolvedValue([]);
    vi.mocked(getCurrentUser).mockResolvedValue(user);
    vi.mocked(getProviders).mockResolvedValue([]);
    vi.mocked(getQuest).mockImplementation(async (questId) => quest(questId));
    vi.mocked(getQuests).mockResolvedValue([quest("quest-1"), quest("quest-2")]);
    vi.mocked(getWorkflowCapabilities).mockResolvedValue([]);
    vi.mocked(getWorkflowCanvasTemplate).mockResolvedValue({
      core_flow_agent_ids: [],
      edges: [],
      entry_agent_id: "demand_validator",
      lanes: [],
      nodes: [],
      terminal_agent_id: "paper_meeting_writer",
    });
    vi.mocked(runStage).mockImplementation(async (stageId) => stage(stageId.slice(6)));
  });

  it("keeps the new Quest stages and actions when an old run refresh resolves", async () => {
    const staleStages = deferred<StageCard[]>();
    const staleActions = deferred<WorkflowNextActionsResponse>();
    let questOneStageCalls = 0;
    let questOneActionCalls = 0;
    vi.mocked(getQuestStages).mockImplementation((questId) => {
      if (questId !== "quest-1") {
        return Promise.resolve([stage(questId)]);
      }
      questOneStageCalls += 1;
      return questOneStageCalls === 1
        ? Promise.resolve([stage(questId)])
        : staleStages.promise;
    });
    vi.mocked(getWorkflowNextActions).mockImplementation((questId) => {
      if (questId !== "quest-1") {
        return Promise.resolve(nextActions(questId));
      }
      questOneActionCalls += 1;
      return questOneActionCalls === 1
        ? Promise.resolve(nextActions(questId))
        : staleActions.promise;
    });
    const userEvents = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/?quest=quest-1"]}>
        <AuthProvider>
          <I18nProvider>
            <Routes>
              <Route element={<CanvasWorkspacePage />} path="/" />
            </Routes>
          </I18nProvider>
        </AuthProvider>
      </MemoryRouter>,
    );
    await screen.findByRole("heading", { name: "Quest quest-1" });
    await userEvents.click(screen.getByRole("button", { name: "Run agent" }));
    await waitFor(() => expect(questOneStageCalls).toBe(2));

    await userEvents.selectOptions(screen.getByRole("combobox", { name: "Quest" }), "quest-2");
    await screen.findByRole("heading", { name: "Quest quest-2" });

    await act(async () => {
      staleStages.resolve([{ ...stage("quest-1"), status: "complete" }]);
      staleActions.resolve(nextActions("quest-1"));
      await staleStages.promise;
      await staleActions.promise;
    });

    expect(screen.getByText("Run agent: Stage quest-2")).toBeInTheDocument();
    expect(screen.queryByText("Run agent: Stage quest-1")).not.toBeInTheDocument();
  });
});
