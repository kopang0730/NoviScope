import { useState } from "react";
import { Link } from "react-router-dom";
import type { Quest, StageCard } from "../api/types";
import { Badge } from "./badge";
import { Button, buttonClassName } from "./button";
import { Card, CardHeading } from "./card";
import { ResearchCanvas } from "./research-canvas";
import { StageRunSummary } from "./stage-output-summary";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import { canRunStage } from "../lib/stages";
import { questTone, stageTone } from "../lib/status-tones";

export function QuestWorkflowPanel({
  detailError,
  detailLoading,
  onRunStage,
  runningStageId,
  selectedQuest,
  selectedQuestId,
  stageRunError,
  stages,
}: {
  readonly detailError: string | null;
  readonly detailLoading: boolean;
  readonly onRunStage: (stageId: string) => void;
  readonly runningStageId: string | null;
  readonly selectedQuest: Quest | null;
  readonly selectedQuestId: string | null;
  readonly stageRunError: string | null;
  readonly stages: readonly StageCard[];
}) {
  const { t } = useI18n();
  const [viewMode, setViewMode] = useState<"canvas" | "list">("canvas");

  return (
    <Card className="min-w-0">
      <CardHeading description={t("workflowDescription")} title={t("workflowTitle")} />
      {!selectedQuestId ? <p className="mt-4 text-sm text-slate-500">{t("selectQuestForStages")}</p> : null}
      {detailError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{detailError}</p> : null}
      {stageRunError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{stageRunError}</p> : null}
      {detailLoading ? <p className="mt-4 text-sm text-slate-500">{t("loadingQuestDetail")}</p> : null}
      {selectedQuest ? (
        <div className="mt-6 min-w-0 space-y-5">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("currentQuest")}</p>
                <h3 className="text-base font-semibold text-slate-900">{selectedQuest.title}</h3>
              </div>
              <Badge tone={questTone(selectedQuest.status)}>{labelFromEnum(selectedQuest.status)}</Badge>
            </div>
            <div className="grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
              <p>
                {t("created")} {formatDateTime(selectedQuest.created_at)}
              </p>
              <p>
                {t("updated")} {formatDateTime(selectedQuest.updated_at)}
              </p>
            </div>
          </div>

          <div className="inline-flex w-fit rounded-lg border border-slate-200 bg-slate-50 p-1">
            <button
              className={[
                "rounded-md px-3 py-1.5 text-sm font-medium transition",
                viewMode === "canvas" ? "bg-white text-teal-700 shadow-sm" : "text-slate-600 hover:text-slate-900",
              ].join(" ")}
              onClick={() => setViewMode("canvas")}
              type="button"
            >
              {t("canvasView")}
            </button>
            <button
              className={[
                "rounded-md px-3 py-1.5 text-sm font-medium transition",
                viewMode === "list" ? "bg-white text-teal-700 shadow-sm" : "text-slate-600 hover:text-slate-900",
              ].join(" ")}
              onClick={() => setViewMode("list")}
              type="button"
            >
              {t("stageListView")}
            </button>
          </div>

          {stages.length === 0 ? (
            <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
              {t("noStagesFound")}
            </p>
          ) : viewMode === "canvas" ? (
            <ResearchCanvas
              onRunStage={onRunStage}
              runningStageId={runningStageId}
              selectedQuest={selectedQuest}
              stages={stages}
            />
          ) : (
            <div className="space-y-3">
              {stages.map((stage, index) => (
                <div className="rounded-lg border border-slate-200 p-4" key={stage.id}>
                  <div className="flex items-start gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-teal-200 bg-teal-50 text-sm font-semibold text-teal-700">
                      {index + 1}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-col gap-3">
                        <div>
                          <p className="font-medium text-slate-900">{stage.title}</p>
                          <p className="mt-1 text-sm text-slate-500">{stage.agent_id}</p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge>
                          {canRunStage(stage) ? (
                            <Button loading={runningStageId === stage.id} onClick={() => onRunStage(stage.id)} size="sm">
                              {t("runStage")}
                            </Button>
                          ) : null}
                          <Link className={buttonClassName({ size: "sm", variant: "secondary" })} to={`/stages/${stage.id}?quest=${selectedQuest.id}`}>
                            {t("open")}
                          </Link>
                        </div>
                      </div>
                      <StageRunSummary stage={stage} />
                      {stage.review_notes ? (
                        <p className="mt-2 text-xs text-slate-500">
                          {t("reviewNotes")}: {stage.review_notes}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </Card>
  );
}
