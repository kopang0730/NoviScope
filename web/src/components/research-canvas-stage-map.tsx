import type { Quest, StageCard } from "../api/types";
import { type TranslationKey, useI18n } from "../i18n/i18n-context";
import { buildStageDetails, phaseKeyForAgent } from "../lib/research-canvas-data";
import type { StageRunGate } from "../lib/stage-run-gate";
import { stageTone } from "../lib/status-tones";
import { Badge } from "./badge";
import { CanvasStageNode } from "./research-canvas-stage-node";

export const canvasStageFilters = [
  { id: "all", labelKey: "canvasFilterAll" },
  { id: "next_action", labelKey: "canvasFilterNextAction" },
  { id: "blocked", labelKey: "canvasFilterBlocked" },
  { id: "review", labelKey: "canvasFilterReview" },
  { id: "complete", labelKey: "canvasFilterComplete" },
] as const satisfies readonly { readonly id: string; readonly labelKey: TranslationKey }[];

export type CanvasStageFilter = (typeof canvasStageFilters)[number]["id"];

type ResearchCanvasStageMapProps = {
  readonly filterCounts: Record<CanvasStageFilter, number>;
  readonly nextActionStage: StageCard | null;
  readonly onFilterChange: (filter: CanvasStageFilter) => void;
  readonly onRunStage: (stageId: string) => void;
  readonly onSelectStage: (stageId: string) => void;
  readonly runningStageId: string | null;
  readonly selectedQuest: Quest;
  readonly selectedStage: StageCard | null;
  readonly stageFilter: CanvasStageFilter;
  readonly stageRunGates: ReadonlyMap<string, StageRunGate>;
  readonly stages: readonly StageCard[];
  readonly visibleStages: readonly StageCard[];
};

function legendDotClassName(tone: "blocked" | "complete" | "ready") {
  if (tone === "complete") {
    return "bg-emerald-400";
  }
  if (tone === "blocked") {
    return "bg-rose-400";
  }
  return "bg-teal-500";
}

function LegendItem({ label, tone }: { readonly label: string; readonly tone: "blocked" | "complete" | "ready" }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs font-medium text-slate-600">
      <span className={["h-2 w-2 rounded-full", legendDotClassName(tone)].join(" ")} />
      {label}
    </span>
  );
}

export function ResearchCanvasStageMap({
  filterCounts,
  nextActionStage,
  onFilterChange,
  onRunStage,
  onSelectStage,
  runningStageId,
  selectedQuest,
  selectedStage,
  stageFilter,
  stageRunGates,
  stages,
  visibleStages,
}: ResearchCanvasStageMapProps) {
  const { t } = useI18n();

  return (
    <div className="min-w-0 overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900">{t("canvasMapTitle")}</p>
          <p className="mt-1 text-sm text-slate-500">{t("canvasMapDescription")}</p>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
            <LegendItem label={t("canvasMapLegendReady")} tone="ready" />
            <LegendItem label={t("canvasMapLegendComplete")} tone="complete" />
            <LegendItem label={t("canvasMapLegendBlocked")} tone="blocked" />
          </div>
        </div>
        <Badge tone={nextActionStage ? stageTone(nextActionStage.status) : "gray"}>
          {nextActionStage ? t("canvasNextAction") : t("canvasNoNextAction")}
        </Badge>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-200 px-4 py-3">
        {canvasStageFilters.map((filter) => {
          const isActive = stageFilter === filter.id;
          return (
            <button
              className={[
                "rounded-full border px-3 py-1.5 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2",
                isActive
                  ? "border-teal-600 bg-teal-600 text-white shadow-sm"
                  : "border-slate-200 bg-white text-slate-600 hover:border-teal-200 hover:bg-teal-50 hover:text-teal-800",
              ].join(" ")}
              key={filter.id}
              onClick={() => onFilterChange(filter.id)}
              type="button"
            >
              {t(filter.labelKey)} · {filterCounts[filter.id]}
            </button>
          );
        })}
      </div>

      <div className="overflow-x-auto px-4 py-4">
        {visibleStages.length > 0 ? (
          <div className="grid w-max min-w-full auto-cols-[minmax(260px,1fr)] grid-flow-col gap-4">
            {visibleStages.map((stage) => {
              const stageRunGate = stageRunGates.get(stage.id);

              if (!stageRunGate) {
                return null;
              }

              return (
                <CanvasStageNode
                  details={buildStageDetails(stage, t)}
                  index={stages.findIndex((candidate) => candidate.id === stage.id)}
                  isNextAction={nextActionStage?.id === stage.id}
                  isSelected={selectedStage?.id === stage.id}
                  key={stage.id}
                  onRunStage={onRunStage}
                  onSelectStage={onSelectStage}
                  phaseLabel={t(phaseKeyForAgent(stage.agent_id))}
                  runningStageId={runningStageId}
                  selectedQuest={selectedQuest}
                  stage={stage}
                  stageRunGate={stageRunGate}
                  total={stages.length}
                />
              );
            })}
          </div>
        ) : (
          <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
            {t("canvasFilterEmpty")}
          </p>
        )}
      </div>
    </div>
  );
}
