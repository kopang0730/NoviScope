import type { KeyboardEvent } from "react";
import { useI18n } from "../i18n/i18n-context";
import {
  buildMacroPhasePresentation,
  macroPhaseStateKey,
  type MacroPhaseState,
} from "../lib/research-phase-projection";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import type { MacroPhaseId, MacroPhaseView } from "../lib/research-workbench";
import type { StageCard, WorkflowNextAction } from "../api/types";
import { Badge, type BadgeTone } from "./badge";

export type ResearchPhasePathProps = {
  readonly nextActionPhaseId: MacroPhaseId | null;
  readonly nextAction: WorkflowNextAction | null;
  readonly onSelectPhase: (phaseId: MacroPhaseId) => void;
  readonly phases: readonly MacroPhaseView[];
  readonly providerReadinessData: ProviderReadinessData;
  readonly selectedPhaseId: MacroPhaseId;
  readonly stages: readonly StageCard[];
};

function phaseTone(state: MacroPhaseState): BadgeTone {
  switch (state) {
    case "blocked":
      return "red";
    case "complete":
      return "green";
    case "pending":
    case "planned":
      return "gray";
    case "review_required":
    case "running":
      return "amber";
    case "runnable":
      return "teal";
  }
}

function nextPhaseIndex(key: string, currentIndex: number, phaseCount: number) {
  switch (key) {
    case "ArrowDown":
    case "ArrowRight":
      return (currentIndex + 1) % phaseCount;
    case "ArrowLeft":
    case "ArrowUp":
      return (currentIndex - 1 + phaseCount) % phaseCount;
    case "End":
      return phaseCount - 1;
    case "Home":
      return 0;
    default:
      return null;
  }
}

export function ResearchPhasePath({
  nextAction,
  nextActionPhaseId,
  onSelectPhase,
  phases,
  providerReadinessData,
  selectedPhaseId,
  stages,
}: ResearchPhasePathProps) {
  const { t } = useI18n();

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, currentIndex: number) {
    const targetIndex = nextPhaseIndex(event.key, currentIndex, phases.length);
    if (targetIndex === null) {
      return;
    }

    const targetPhase = phases[targetIndex];
    if (!targetPhase) {
      return;
    }

    event.preventDefault();
    onSelectPhase(targetPhase.definition.id);
    document.getElementById(`research-phase-${targetPhase.definition.id}`)?.focus();
  }

  return (
    <nav aria-label={t("researchCanvasTitle")} id="research-phase-path">
      <ol className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {phases.map((phase, index) => {
          const presentation = buildMacroPhasePresentation({
            nextAction,
            phase,
            t,
            providerReadinessData,
            stages,
          });
          const phaseTitle = t(presentation.titleKey);
          const isSelected = phase.definition.id === selectedPhaseId;
          const isCurrentAction = phase.definition.id === nextActionPhaseId;

          return (
            <li className="relative min-w-0" key={phase.definition.id}>
              <button
                aria-label={`${t("canvasPhaseLabel")} ${index + 1}: ${phaseTitle}`}
                aria-pressed={isSelected}
                className={[
                  "flex h-full min-h-44 w-full flex-col rounded-lg border bg-white p-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2",
                  isSelected
                    ? "border-teal-500 shadow-panel"
                    : isCurrentAction
                      ? "border-teal-300"
                      : "border-slate-200 hover:border-slate-300 hover:bg-slate-50",
                ].join(" ")}
                id={`research-phase-${phase.definition.id}`}
                onClick={() => onSelectPhase(phase.definition.id)}
                onKeyDown={(event) => handleKeyDown(event, index)}
                type="button"
              >
                <span className="block w-full min-w-0">
                  <span className="flex items-start justify-between gap-2">
                    <span className="block text-xs font-semibold text-slate-500">
                      {t("canvasPhaseLabel")} {index + 1}
                    </span>
                    <Badge tone={phaseTone(presentation.state)}>
                      {t(macroPhaseStateKey(presentation.state))}
                    </Badge>
                  </span>
                  <span className="mt-1 block text-pretty text-sm font-semibold text-slate-950">
                    {phaseTitle}
                  </span>
                </span>

                <span className="mt-3 block text-xs leading-5 text-slate-600">
                  {t(presentation.flow.inputKey)} → {t(presentation.flow.outputKey)}
                </span>
                <span className="mt-2 block text-xs leading-5 text-slate-500">
                  <span className="font-semibold text-slate-600">{t("canvasPhaseSignal")}:</span>{" "}
                  {presentation.signal}
                </span>

                <span className="mt-auto grid w-full min-w-0 gap-1.5 pt-3">
                  {phase.agents.map((agent) => (
                    <span
                      aria-label={`${agent.displayName}: ${
                        agent.status === "planned"
                          ? t("canvasRolePlanned")
                          : t("canvasRoleImplemented")
                      }`}
                      aria-disabled={agent.status === "planned" ? "true" : undefined}
                      className={[
                        "grid min-h-6 w-full min-w-0 gap-0.5 rounded border px-2 py-1 text-xs",
                        agent.status === "planned"
                          ? "border-slate-200 bg-slate-50 text-slate-500"
                          : "border-teal-200 bg-teal-50 text-teal-800",
                      ].join(" ")}
                      key={agent.agentId}
                      role="status"
                    >
                      <span className="min-w-0 break-words text-pretty">{agent.displayName}</span>
                      <span className="font-semibold leading-4">
                        {agent.status === "planned"
                          ? t("canvasRolePlanned")
                          : t("canvasRoleImplemented")}
                      </span>
                    </span>
                  ))}
                </span>

                {isCurrentAction ? (
                  <span className="mt-3 text-xs font-semibold text-teal-700">
                    {t("canvasPhaseCurrentAction")}
                  </span>
                ) : null}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
