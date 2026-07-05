import { useEffect, useState } from "react";
import type { Quest, StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import {
  buildStageDetails,
  findNextActionStage,
  needsHumanReview,
  phaseKeyForAgent,
} from "../lib/research-canvas-data";
import { getStageRunGate } from "../lib/stage-run-gate";
import { stageTone } from "../lib/status-tones";
import { Badge } from "./badge";
import { ResearchCanvasInspector } from "./research-canvas-inspector";
import { CanvasStageNode } from "./research-canvas-stage-node";

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
  const nextActionStage = findNextActionStage(stages, providerReadinessData);
  const selectedStage = stages.find((stage) => stage.id === selectedStageId) ?? nextActionStage ?? stages[0] ?? null;
  const completeCount = stages.filter((stage) => stage.status === "complete").length;
  const blockedCount = stages.filter((stage) => stage.status === "blocked").length;
  const reviewCount = stages.filter(needsHumanReview).length;
  const progressLabel = stages.length > 0 ? `${completeCount}/${stages.length}` : "0/0";

  useEffect(() => {
    if (!selectedStage || selectedStage.id === selectedStageId) {
      return;
    }
    setSelectedStageId(selectedStage.id);
  }, [selectedStage, selectedStageId]);

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

      <div className="mt-4 grid gap-4 2xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-4 flex min-w-[980px] flex-col gap-2 border-b border-slate-200 pb-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-900">{t("canvasMapTitle")}</p>
              <p className="mt-1 text-sm text-slate-500">{t("canvasMapDescription")}</p>
            </div>
            <Badge tone={nextActionStage ? stageTone(nextActionStage.status) : "gray"}>
              {nextActionStage ? t("canvasNextAction") : t("canvasNoNextAction")}
            </Badge>
          </div>
          <div className="grid min-w-[980px] grid-cols-5 gap-3">
            {stages.map((stage, index) => (
              <CanvasStageNode
                details={buildStageDetails(stage, t)}
                index={index}
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
