import {
  demandValidatorAgentId,
  experimentPlannerAgentId,
  ideaGeneratorAgentId,
  literatureScoutAgentId,
  paperMeetingWriterAgentId,
} from "./stages";
import type { StageCard, WorkflowAgentCapability } from "../api/types";

const researchRefinerAgentId = "research_refiner";
const gapAnalystAgentId = "gap_analyst";
const codeRunnerAgentId = "code_runner";
const evidenceAuditorAgentId = "evidence_auditor";

export type MacroPhaseId =
  | "demand_scope"
  | "literature_gap"
  | "hypothesis_idea"
  | "experiment_verification"
  | "paper_meeting";

export type MacroPhaseDefinition = {
  readonly id: MacroPhaseId;
  readonly agentIds: readonly string[];
  readonly primaryAgentId: string;
};

export type MacroPhaseAgentView = {
  readonly agentId: string;
  readonly displayName: string;
  readonly status: "implemented" | "planned";
  readonly canConfigureProvider: boolean;
};

export type MacroPhaseView = {
  readonly definition: MacroPhaseDefinition;
  readonly primaryStage: StageCard | null;
  readonly agents: readonly MacroPhaseAgentView[];
};

export const macroPhaseDefinitions: readonly MacroPhaseDefinition[] = [
  {
    id: "demand_scope",
    primaryAgentId: demandValidatorAgentId,
    agentIds: [demandValidatorAgentId, researchRefinerAgentId],
  },
  {
    id: "literature_gap",
    primaryAgentId: literatureScoutAgentId,
    agentIds: [literatureScoutAgentId, gapAnalystAgentId],
  },
  {
    id: "hypothesis_idea",
    primaryAgentId: ideaGeneratorAgentId,
    agentIds: [ideaGeneratorAgentId],
  },
  {
    id: "experiment_verification",
    primaryAgentId: experimentPlannerAgentId,
    agentIds: [experimentPlannerAgentId, codeRunnerAgentId, evidenceAuditorAgentId],
  },
  {
    id: "paper_meeting",
    primaryAgentId: paperMeetingWriterAgentId,
    agentIds: [paperMeetingWriterAgentId],
  },
];

export function phaseForAgentId(agentId: string): MacroPhaseId | null {
  return macroPhaseDefinitions.find((phase) => phase.agentIds.includes(agentId))?.id ?? null;
}

function buildMacroPhaseAgentView(
  agentId: string,
  capabilities: readonly WorkflowAgentCapability[],
): MacroPhaseAgentView {
  const capability = capabilities.find((item) => item.agent_id === agentId);

  if (!capability) {
    return {
      agentId,
      displayName: agentId,
      status: "planned",
      canConfigureProvider: false,
    };
  }

  return {
    agentId,
    displayName: capability.display_name,
    status: capability.automation_status,
    canConfigureProvider:
      capability.stage_runner_available && capability.provider_requirement === "model_provider",
  };
}

export function buildMacroPhaseViews(
  stages: readonly StageCard[],
  capabilities: readonly WorkflowAgentCapability[],
): readonly MacroPhaseView[] {
  return macroPhaseDefinitions.map((definition) => ({
    definition,
    primaryStage: stages.find((stage) => stage.agent_id === definition.primaryAgentId) ?? null,
    agents: definition.agentIds.map((agentId) => buildMacroPhaseAgentView(agentId, capabilities)),
  }));
}
