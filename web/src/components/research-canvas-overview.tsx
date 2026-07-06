import type { StageCard, StageStatus } from "../api/types";
import { type TranslationKey, useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { buildStageDetails, needsHumanReview, phaseKeyForAgent } from "../lib/research-canvas-data";
import {
  getLocalizedStageRunGateReason,
  type StageRunGate,
} from "../lib/stage-run-gate";
import { stageTone } from "../lib/status-tones";
import { Badge } from "./badge";

type Translate = (key: TranslationKey) => string;

type ResearchCanvasOverviewProps = {
  readonly nextActionStage: StageCard | null;
  readonly onSelectStage: (stageId: string) => void;
  readonly selectedStage: StageCard | null;
  readonly stageRunGates: ReadonlyMap<string, StageRunGate>;
  readonly stages: readonly StageCard[];
};

function overviewNodeClassName(stage: StageCard, isSelected: boolean, isNextAction: boolean) {
  const statusClassNames: Record<StageStatus, string> = {
    blocked: "border-rose-300 bg-rose-50 hover:border-rose-400",
    complete: "border-emerald-300 bg-emerald-50 hover:border-emerald-400",
    pending: "border-slate-200 bg-white hover:border-teal-300 hover:bg-teal-50",
    running: "border-amber-300 bg-amber-50 hover:border-amber-400",
  };

  return [
    "flex min-h-[172px] w-full flex-col rounded-lg border px-3 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2",
    statusClassNames[stage.status],
    isSelected ? "ring-2 ring-teal-500 ring-offset-2" : "",
    !isSelected && isNextAction ? "shadow-[0_0_0_2px_rgba(20,184,166,0.25)]" : "",
  ].join(" ");
}

function overviewRailClassName(status: StageStatus) {
  const statusClassNames: Record<StageStatus, string> = {
    blocked: "bg-rose-400",
    complete: "bg-emerald-400",
    pending: "bg-slate-300",
    running: "bg-amber-400",
  };

  return statusClassNames[status];
}

function buildOverviewSignal(stage: StageCard, t: Translate, stageRunGate: StageRunGate) {
  if (stage.human_approved === true) {
    return t("canvasGateApproved");
  }
  if (stage.human_approved === false) {
    return t("canvasGateRejected");
  }
  if (needsHumanReview(stage)) {
    return t("humanReviewRequired");
  }
  if (stageRunGate.canRun) {
    return t("canvasReadyToRun");
  }
  if (stage.status === "complete") {
    return t("canvasOutputReady");
  }
  return getLocalizedStageRunGateReason(stageRunGate, t);
}

export function ResearchCanvasOverview({
  nextActionStage,
  onSelectStage,
  selectedStage,
  stageRunGates,
  stages,
}: ResearchCanvasOverviewProps) {
  const { t } = useI18n();

  return (
    <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-4">
        <p className="text-sm font-semibold text-slate-900">{t("canvasOverviewTitle")}</p>
        <p className="mt-1 text-sm text-slate-500">{t("canvasOverviewDescription")}</p>
      </div>
      <div className="grid gap-3 px-4 py-4 sm:grid-cols-2 xl:grid-cols-3">
        {stages.map((stage, index) => {
          const stageRunGate = stageRunGates.get(stage.id);

          if (!stageRunGate) {
            return null;
          }

          const stageDetails = buildStageDetails(stage, t);
          const isSelected = selectedStage?.id === stage.id;
          const isNextAction = nextActionStage?.id === stage.id;
          const overviewSignal = buildOverviewSignal(stage, t, stageRunGate);

          return (
            <button
              aria-pressed={isSelected}
              className={overviewNodeClassName(stage, isSelected, isNextAction)}
              key={stage.id}
              onClick={() => onSelectStage(stage.id)}
              type="button"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white bg-white text-sm font-semibold text-slate-900 shadow-sm">
                    {index + 1}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold text-teal-700">{t(phaseKeyForAgent(stage.agent_id))}</p>
                    <h3 className="mt-1 line-clamp-2 text-sm font-semibold text-slate-950">{stage.title}</h3>
                  </div>
                </div>
                <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge>
              </div>

              <div className="mt-3 flex items-start gap-2">
                <span className={["mt-1 h-12 w-1 shrink-0 rounded-full", overviewRailClassName(stage.status)].join(" ")} />
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    {isNextAction ? t("canvasNextAction") : t("canvasOverviewSignal")}
                  </p>
                  <p className="mt-1 line-clamp-2 text-xs font-medium text-slate-800">{overviewSignal}</p>
                </div>
              </div>

              <div className="mt-auto pt-3">
                {stageDetails[0] ? (
                  <p className="line-clamp-2 rounded-md bg-white/75 px-3 py-2 text-xs text-slate-700">
                    <span className="font-semibold text-slate-800">{stageDetails[0].label}: </span>
                    {stageDetails[0].value}
                  </p>
                ) : (
                  <p className="rounded-md border border-dashed border-slate-200 bg-white/60 px-3 py-2 text-xs text-slate-500">
                    {t("canvasWaitingForOutput")}
                  </p>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
