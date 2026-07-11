import { describe, expect, it } from "vitest";
import type { StageCard, WorkflowAgentCapability } from "../api/types";
import {
  buildMacroPhaseViews,
  macroPhaseDefinitions,
  phaseForAgentId,
} from "./research-workbench";

const stages = [
  {
    id: "stage-demand",
    quest_id: "quest-1",
    agent_id: "demand_validator",
    title: "Demand validation",
    status: "complete",
    confidence: "high",
    summary: "Demand evidence is ready for review.",
    input_payload: {},
    output_payload: {},
    evidence_payload: {},
    human_approved: null,
    review_notes: "",
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z",
  },
] satisfies readonly StageCard[];

const capabilities = [
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
] satisfies readonly WorkflowAgentCapability[];

describe("research workbench phases", () => {
  it("maps all nine agents into five ordered macro phases", () => {
    expect(macroPhaseDefinitions.map((phase) => phase.id)).toEqual([
      "demand_scope",
      "literature_gap",
      "hypothesis_idea",
      "experiment_verification",
      "paper_meeting",
    ]);
    expect(new Set(macroPhaseDefinitions.flatMap((phase) => phase.agentIds)).size).toBe(9);
    expect(phaseForAgentId("evidence_auditor")).toBe("experiment_verification");
  });

  it("builds five phase views from stage and capability truth", () => {
    const phases = buildMacroPhaseViews(stages, capabilities);

    expect(phases).toHaveLength(5);
    expect(phases[0]?.primaryStage?.agent_id).toBe("demand_validator");
    expect(phases[0]?.agents.find((agent) => agent.agentId === "research_refiner")?.status).toBe(
      "planned",
    );
    expect(
      phases[3]?.agents.find((agent) => agent.agentId === "code_runner")?.canConfigureProvider,
    ).toBe(false);
    expect(phases[3]?.agents.find((agent) => agent.agentId === "evidence_auditor")).toEqual({
      agentId: "evidence_auditor",
      displayName: "evidence_auditor",
      status: "planned",
      canConfigureProvider: false,
    });
  });
});
