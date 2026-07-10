import { describe, expect, it } from "vitest";
import { macroPhaseDefinitions, phaseForAgentId } from "./research-workbench";

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
});
