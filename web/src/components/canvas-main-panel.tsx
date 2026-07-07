import type { Quest, StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import { questTone } from "../lib/status-tones";
import { Badge } from "./badge";
import { CanvasReviewPacketButton } from "./canvas-review-packet-button";
import { Card, CardHeading } from "./card";
import { ResearchCanvas } from "./research-canvas";

export function CanvasMainPanel({
  detailError,
  detailLoading,
  onRunStage,
  providerReadinessData,
  runningStageId,
  selectedQuest,
  selectedQuestId,
  stageRunError,
  stages,
}: {
  readonly detailError: string | null;
  readonly detailLoading: boolean;
  readonly onRunStage: (stageId: string) => void;
  readonly providerReadinessData: ProviderReadinessData;
  readonly runningStageId: string | null;
  readonly selectedQuest: Quest | null;
  readonly selectedQuestId: string | null;
  readonly stageRunError: string | null;
  readonly stages: readonly StageCard[];
}) {
  const { t } = useI18n();

  return (
    <div className="min-w-0 space-y-4">
      <Card className="overflow-hidden">
        <CardHeading
          action={<CanvasReviewPacketButton quest={selectedQuest} stages={stages} />}
          description={t("canvasWorkspaceMainDescription")}
          title={t("researchCanvasTitle")}
        />
        {!selectedQuestId ? <p className="mt-4 text-sm text-slate-500">{t("selectQuestForStages")}</p> : null}
        {detailError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{detailError}</p> : null}
        {stageRunError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{stageRunError}</p> : null}
        {detailLoading ? <p className="mt-4 text-sm text-slate-500">{t("loadingQuestDetail")}</p> : null}

        {selectedQuest ? (
          <div className="mt-5 space-y-4">
            <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("currentQuest")}</p>
                <h2 className="mt-1 text-xl font-semibold text-slate-950">{selectedQuest.title}</h2>
                <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">{selectedQuest.initial_direction}</p>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                <Badge tone={questTone(selectedQuest.status)}>{labelFromEnum(selectedQuest.status)}</Badge>
                <Badge tone="gray">
                  {t("updated")} {formatDateTime(selectedQuest.updated_at)}
                </Badge>
              </div>
            </div>

            {stages.length === 0 ? (
              <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
                {t("noStagesFound")}
              </p>
            ) : (
              <ResearchCanvas
                onRunStage={onRunStage}
                providerReadinessData={providerReadinessData}
                runningStageId={runningStageId}
                selectedQuest={selectedQuest}
                showHeading={false}
                stages={stages}
              />
            )}
          </div>
        ) : null}
      </Card>
    </div>
  );
}
