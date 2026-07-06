import { useEffect, useMemo, useState } from "react";
import type { Quest, StageCard, StageStatus } from "../api/types";
import { type TranslationKey, useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import {
  buildStageDetails,
  findNextActionStage,
  needsHumanReview,
  phaseKeyForAgent,
} from "../lib/research-canvas-data";
import {
  getLocalizedStageRunGateReason,
  getStageRunGate,
  type StageRunGate,
} from "../lib/stage-run-gate";
import { stageTone } from "../lib/status-tones";
import { Badge } from "./badge";
import { ResearchCanvasInspector } from "./research-canvas-inspector";
import { CanvasStageNode } from "./research-canvas-stage-node";

const canvasStageFilters = [
  { id: "all", labelKey: "canvasFilterAll" },
  { id: "next_action", labelKey: "canvasFilterNextAction" },
  { id: "blocked", labelKey: "canvasFilterBlocked" },
  { id: "review", labelKey: "canvasFilterReview" },
  { id: "complete", labelKey: "canvasFilterComplete" },
] as const satisfies readonly { readonly id: string; readonly labelKey: TranslationKey }[];

type CanvasStageFilter = (typeof canvasStageFilters)[number]["id"];

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

function buildOverviewSignal(
  stage: StageCard,
  t: ReturnType<typeof useI18n>["t"],
  stageRunGate: StageRunGate,
) {
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

function stageMatchesFilter(stage: StageCard, filter: CanvasStageFilter, nextActionStage: StageCard | null) {
  switch (filter) {
    case "all":
      return true;
    case "next_action":
      return nextActionStage?.id === stage.id;
    case "blocked":
      return stage.status === "blocked";
    case "review":
      return needsHumanReview(stage);
    case "complete":
      return stage.status === "complete";
  }
}

export function ResearchCanvas({
  onRunStage,
  providerReadinessData,
  runningStageId,
  selectedQuest,
  showHeading = true,
  stages,
}: {
  readonly onRunStage: (stageId: string) => void;
  readonly providerReadinessData: ProviderReadinessData;
  readonly runningStageId: string | null;
  readonly selectedQuest: Quest;
  readonly showHeading?: boolean;
  readonly stages: readonly StageCard[];
}) {
  const { t } = useI18n();
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);
  const [stageFilter, setStageFilter] = useState<CanvasStageFilter>("all");
  const nextActionStage = findNextActionStage(stages, providerReadinessData);
  const completeCount = stages.filter((stage) => stage.status === "complete").length;
  const blockedCount = stages.filter((stage) => stage.status === "blocked").length;
  const reviewCount = stages.filter(needsHumanReview).length;
  const progressLabel = stages.length > 0 ? `${completeCount}/${stages.length}` : "0/0";
  const visibleStages = useMemo(
    () => stages.filter((stage) => stageMatchesFilter(stage, stageFilter, nextActionStage)),
    [nextActionStage, stageFilter, stages],
  );
  const selectedStage =
    visibleStages.find((stage) => stage.id === selectedStageId) ??
    (stageFilter === "all" ? nextActionStage : null) ??
    visibleStages[0] ??
    null;
  const filterCounts: Record<CanvasStageFilter, number> = {
    all: stages.length,
    blocked: blockedCount,
    complete: completeCount,
    next_action: nextActionStage ? 1 : 0,
    review: reviewCount,
  };

  useEffect(() => {
    if (!selectedStage || selectedStage.id === selectedStageId) {
      return;
    }
    setSelectedStageId(selectedStage.id);
  }, [selectedStage, selectedStageId]);

  function selectStageFromOverview(stageId: string) {
    setStageFilter("all");
    setSelectedStageId(stageId);
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      {showHeading ? (
        <div className="flex flex-col gap-2 px-1 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-900">{t("researchCanvasTitle")}</p>
            <p className="mt-1 text-sm text-slate-500">{t("researchCanvasDescription")}</p>
          </div>
          <Badge tone="gray">
            {t("updated")} {formatDateTime(selectedQuest.updated_at)}
          </Badge>
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("canvasProgress")}</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">{progressLabel}</p>
          <p className="mt-1 text-xs text-slate-500">{t("canvasCompleteCount")}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("overviewBlockedStages")}</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">{blockedCount}</p>
          <p className="mt-1 text-xs text-slate-500">{t("canvasBlockedCount")}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("stageReviewPending")}</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">{reviewCount}</p>
          <p className="mt-1 text-xs text-slate-500">{t("canvasReviewCount")}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("canvasNextAction")}</p>
          {nextActionStage ? (
            <div className="mt-1 grid gap-2">
              <p className="line-clamp-2 break-words text-sm font-semibold text-slate-950">{nextActionStage.title}</p>
              <div>
                <Badge tone={stageTone(nextActionStage.status)}>{labelFromEnum(nextActionStage.status)}</Badge>
              </div>
            </div>
          ) : (
            <p className="mt-1 text-sm font-semibold text-slate-950">{t("canvasNoNextAction")}</p>
          )}
        </div>
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-4">
          <p className="text-sm font-semibold text-slate-900">{t("canvasOverviewTitle")}</p>
          <p className="mt-1 text-sm text-slate-500">{t("canvasOverviewDescription")}</p>
        </div>
        <div className="grid gap-3 px-4 py-4 sm:grid-cols-2 xl:grid-cols-3">
          {stages.map((stage, index) => {
            const stageRunGate = getStageRunGate({ providerReadinessData, stage, stages });
            const stageDetails = buildStageDetails(stage, t);
            const isSelected = selectedStage?.id === stage.id;
            const isNextAction = nextActionStage?.id === stage.id;
            const overviewSignal = buildOverviewSignal(stage, t, stageRunGate);

            return (
              <button
                aria-pressed={isSelected}
                className={overviewNodeClassName(stage, isSelected, isNextAction)}
                key={stage.id}
                onClick={() => selectStageFromOverview(stage.id)}
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

      <div className="mt-4 grid gap-4 2xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="flex flex-col gap-2 border-b border-slate-200 px-4 py-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-900">{t("canvasMapTitle")}</p>
              <p className="mt-1 text-sm text-slate-500">{t("canvasMapDescription")}</p>
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
                  onClick={() => setStageFilter(filter.id)}
                  type="button"
                >
                  {t(filter.labelKey)} · {filterCounts[filter.id]}
                </button>
              );
            })}
          </div>
          <div className="overflow-x-auto px-4 py-4">
            {visibleStages.length > 0 ? (
              <div className="grid w-max min-w-full auto-cols-[minmax(240px,1fr)] grid-flow-col gap-4">
                {visibleStages.map((stage) => (
                  <CanvasStageNode
                    details={buildStageDetails(stage, t)}
                    index={stages.findIndex((candidate) => candidate.id === stage.id)}
                    isNextAction={nextActionStage?.id === stage.id}
                    isSelected={selectedStage?.id === stage.id}
                    key={stage.id}
                    onRunStage={onRunStage}
                    onSelectStage={setSelectedStageId}
                    phaseLabel={t(phaseKeyForAgent(stage.agent_id))}
                    runningStageId={runningStageId}
                    selectedQuest={selectedQuest}
                    stage={stage}
                    stageRunGate={getStageRunGate({ providerReadinessData, stage, stages })}
                    total={stages.length}
                  />
                ))}
              </div>
            ) : (
              <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                {t("canvasFilterEmpty")}
              </p>
            )}
          </div>
        </div>

        {selectedStage ? (
          <ResearchCanvasInspector
            details={buildStageDetails(selectedStage, t)}
            onRunStage={onRunStage}
            runningStageId={runningStageId}
            selectedQuest={selectedQuest}
            stage={selectedStage}
            stageRunGate={getStageRunGate({ providerReadinessData, stage: selectedStage, stages })}
            />
        ) : null}
      </div>
    </div>
  );
}
