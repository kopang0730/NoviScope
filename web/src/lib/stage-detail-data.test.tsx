import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getProviders } from "../api/providers";
import { getQuest, getQuestStages } from "../api/quests";
import type { Quest, StageCard, User, WorkflowNextActionsResponse } from "../api/types";
import { getWorkflowCapabilities, getWorkflowNextActions } from "../api/workflow";
import { useStageDetailData } from "./stage-detail-data";

vi.mock("../api/providers", () => ({ getProviders: vi.fn() }));
vi.mock("../api/quests", () => ({ getQuest: vi.fn(), getQuestStages: vi.fn() }));
vi.mock("../api/workflow", () => ({
  getWorkflowCapabilities: vi.fn(),
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

describe("useStageDetailData selection safety", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getProviders).mockResolvedValue([]);
    vi.mocked(getWorkflowCapabilities).mockResolvedValue([]);
    vi.mocked(getQuest).mockImplementation(async (questId) => quest(questId));
  });

  it("ignores a delayed refresh and mutation callback after stage navigation", async () => {
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
    const { result, rerender } = renderHook(
      ({ questId, stageId }) => useStageDetailData({ currentUser: user, questId, stageId }),
      { initialProps: { questId: "quest-1", stageId: "stage-quest-1" } },
    );
    await waitFor(() => expect(result.current.stage?.id).toBe("stage-quest-1"));
    const staleRefresh = result.current.refresh();
    const staleStageChange = result.current.applyStageChange;

    rerender({ questId: "quest-2", stageId: "stage-quest-2" });
    await waitFor(() => expect(result.current.stage?.id).toBe("stage-quest-2"));
    expect(staleStageChange({ ...stage("quest-1"), status: "complete" })).toBe(false);

    await act(async () => {
      staleStages.resolve([{ ...stage("quest-1"), status: "complete" }]);
      staleActions.resolve(nextActions("quest-1"));
      await expect(staleRefresh).resolves.toBe(false);
    });

    expect(result.current.stage?.id).toBe("stage-quest-2");
    expect(result.current.nextAction?.stage_id).toBe("stage-quest-2");
  });

  it("does not apply a delayed refresh after unmount", async () => {
    const staleStages = deferred<StageCard[]>();
    const staleActions = deferred<WorkflowNextActionsResponse>();
    vi.mocked(getQuestStages)
      .mockResolvedValueOnce([stage("quest-1")])
      .mockReturnValueOnce(staleStages.promise);
    vi.mocked(getWorkflowNextActions)
      .mockResolvedValueOnce(nextActions("quest-1"))
      .mockReturnValueOnce(staleActions.promise);
    const { result, unmount } = renderHook(() => useStageDetailData({
      currentUser: user,
      questId: "quest-1",
      stageId: "stage-quest-1",
    }));
    await waitFor(() => expect(result.current.stage?.id).toBe("stage-quest-1"));
    const staleRefresh = result.current.refresh();

    unmount();
    staleStages.resolve([stage("quest-1")]);
    staleActions.resolve(nextActions("quest-1"));

    await expect(staleRefresh).resolves.toBe(false);
  });
});
