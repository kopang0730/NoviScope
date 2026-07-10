import { useMemo, useState } from "react";
import type {
  StageCard,
  WorkflowAgentCapability,
  WorkflowNextAction,
} from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import {
  buildMacroPhaseViews,
  type MacroPhaseId,
  phaseForAgentId,
} from "../lib/research-workbench";
import { ResearchPhasePath } from "./research-phase-path";
import { StageWorkbenchTabs } from "./stage-workbench-tabs";

export type ResearchCanvasProps = {
  readonly capabilities: readonly WorkflowAgentCapability[];
  readonly nextAction: WorkflowNextAction | null;
  readonly currentUserId: string | null;
  readonly onRunStage: (stageId: string, providerId?: string) => void;
  readonly providerReadinessData: ProviderReadinessData;
  readonly runningStageId: string | null;
  readonly stages: readonly StageCard[];
};

export function ResearchCanvas({
  capabilities,
  nextAction,
  currentUserId,
  onRunStage,
  providerReadinessData,
  runningStageId,
  stages,
}: ResearchCanvasProps) {
  const { t } = useI18n();
  const nextActionPhaseId = nextAction ? phaseForAgentId(nextAction.agent_id) : null;
  const [selectedPhaseId, setSelectedPhaseId] = useState<MacroPhaseId>(
    nextActionPhaseId ?? "demand_scope",
  );
  const phases = useMemo(
    () => buildMacroPhaseViews(stages, capabilities),
    [capabilities, stages],
  );
  const selectedPhase = phases.find((phase) => phase.definition.id === selectedPhaseId) ?? null;
  const selectedPrimaryAgent = selectedPhase?.agents.find(
    (agent) => agent.agentId === selectedPhase.definition.primaryAgentId,
  );
  const selectedStage =
    selectedPrimaryAgent?.status === "implemented" ? selectedPhase?.primaryStage ?? null : null;

  return (
    <div className="space-y-4">
      <ResearchPhasePath
        nextActionPhaseId={nextActionPhaseId}
        onSelectPhase={setSelectedPhaseId}
        phases={phases}
        providerReadinessData={providerReadinessData}
        selectedPhaseId={selectedPhaseId}
        stages={stages}
      />

      {selectedStage ? (
        <StageWorkbenchTabs
          currentUserId={currentUserId}
          mode="compact"
          onRunStage={onRunStage}
          providerReadinessData={providerReadinessData}
          runningStageId={runningStageId}
          stage={selectedStage}
          stages={stages}
        />
      ) : (
        <section className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-5">
          <h2 className="text-sm font-semibold text-slate-900">{t("canvasPhaseUnavailableTitle")}</h2>
          <p className="mt-1 text-sm text-slate-600">{t("canvasPhaseUnavailableDescription")}</p>
        </section>
      )}
    </div>
  );
}
