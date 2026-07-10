import {
  demandValidatorAgentId,
  experimentPlannerAgentId,
  ideaGeneratorAgentId,
  literatureScoutAgentId,
  paperMeetingWriterAgentId,
} from "./stages";

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
