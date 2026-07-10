import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getWorkflowCapabilities,
  getWorkflowCanvasTemplate,
  getWorkflowNextActions,
} from "./workflow";

const workflowCapabilitiesResponse = {
  agents: [
    {
      agent_id: "demand_validator",
      automation_status: "implemented",
      display_name: "Demand Validator",
      provider_requirement: "model_provider",
      stage_runner_available: true,
      status_detail: "Runnable when a compatible model provider is configured.",
      tool_permissions: ["research_direction"],
    },
    {
      agent_id: "research_refiner",
      automation_status: "planned",
      display_name: "Research Refiner",
      provider_requirement: "not_implemented",
      stage_runner_available: false,
      status_detail: "Planned only; no automated stage runner exists yet.",
      tool_permissions: [],
    },
    {
      agent_id: "literature_scout",
      automation_status: "implemented",
      display_name: "Literature Scout",
      provider_requirement: "server_managed",
      stage_runner_available: true,
      status_detail: "Runnable through server-managed research connectors.",
      tool_permissions: ["literature_search"],
    },
    {
      agent_id: "gap_analyst",
      automation_status: "planned",
      display_name: "Gap Analyst",
      provider_requirement: "not_implemented",
      stage_runner_available: false,
      status_detail: "Planned only; no automated stage runner exists yet.",
      tool_permissions: [],
    },
    {
      agent_id: "idea_generator",
      automation_status: "implemented",
      display_name: "Idea Generator",
      provider_requirement: "model_provider",
      stage_runner_available: true,
      status_detail: "Runnable when a compatible model provider is configured.",
      tool_permissions: ["research_direction"],
    },
    {
      agent_id: "experiment_planner",
      automation_status: "implemented",
      display_name: "Experiment Planner",
      provider_requirement: "model_provider",
      stage_runner_available: true,
      status_detail: "Runnable when a compatible model provider is configured.",
      tool_permissions: ["experiment_setup"],
    },
    {
      agent_id: "code_runner",
      automation_status: "planned",
      display_name: "Code Runner",
      provider_requirement: "not_implemented",
      stage_runner_available: false,
      status_detail: "Planned only; no automated stage runner exists yet.",
      tool_permissions: [],
    },
    {
      agent_id: "evidence_auditor",
      automation_status: "planned",
      display_name: "Evidence Auditor",
      provider_requirement: "not_implemented",
      stage_runner_available: false,
      status_detail: "Planned only; no automated stage runner exists yet.",
      tool_permissions: [],
    },
    {
      agent_id: "paper_meeting_writer",
      automation_status: "implemented",
      display_name: "Paper and Meeting Writer",
      provider_requirement: "model_provider",
      stage_runner_available: true,
      status_detail: "Runnable when a compatible model provider is configured.",
      tool_permissions: ["paper_draft"],
    },
  ],
  implemented_count: 5,
  planned_count: 4,
  total_count: 9,
};

const workflowCanvasTemplateResponse = {
  core_flow_agent_ids: [
    "demand_validator",
    "literature_scout",
    "idea_generator",
    "experiment_planner",
    "paper_meeting_writer",
  ],
  edges: [],
  entry_agent_id: "demand_validator",
  lanes: [],
  nodes: [],
  terminal_agent_id: "paper_meeting_writer",
};

const workflowNextActionsResponse = {
  quest_id: "quest-1",
  action_count: 1,
  actions: [
    {
      action_type: "review_stage",
      agent_id: "demand_validator",
      blocking_reason: "human_review_required",
      can_run: false,
      detail: "Review the demand validation output.",
      label: "Review Demand validation",
      priority: 1,
      stage_id: "stage-1",
      stage_status: "complete",
      stage_title: "Demand validation",
    },
  ],
};

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    headers: { "content-type": "application/json" },
  });
}

function requestPath(input: RequestInfo | URL): string {
  if (typeof input === "string") {
    return input;
  }

  if (input instanceof URL) {
    return input.pathname;
  }

  return input.url;
}

function responseForPath(path: string): Response {
  switch (path) {
    case "/api/workflow/capabilities":
      return jsonResponse(workflowCapabilitiesResponse);
    case "/api/workflow/canvas-template":
      return jsonResponse(workflowCanvasTemplateResponse);
    case "/api/quests/quest-1/workflow-next-actions":
      return jsonResponse(workflowNextActionsResponse);
    default:
      throw new Error(`Unexpected request path: ${path}`);
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("workflow API clients", () => {
  it("requests each workflow resource through the API prefix", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) =>
      Promise.resolve(responseForPath(requestPath(input))),
    );
    vi.stubGlobal("fetch", fetchMock);

    expect(await getWorkflowCapabilities()).toHaveLength(9);
    expect((await getWorkflowNextActions("quest-1")).actions[0]?.action_type).toBe("review_stage");
    expect((await getWorkflowCanvasTemplate()).core_flow_agent_ids).toHaveLength(5);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/workflow/capabilities",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/quests/quest-1/workflow-next-actions",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/workflow/canvas-template",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
