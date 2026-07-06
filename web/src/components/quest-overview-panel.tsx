import { Link } from "react-router-dom";
import type { Quest, StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import { downloadTextFile } from "../lib/download-file";
import { buildPreviewData, findNextStage, parseIntakeBrief, summarizeProgress } from "../lib/quest-overview";
import { buildQuestReviewPacket } from "../lib/quest-review-export";
import { paperMeetingWriterAgentId } from "../lib/stages";
import { questTone, stageTone } from "../lib/status-tones";
import {
  getLocalizedWorkflowReadinessReason,
  getWorkflowStageReadiness,
} from "../lib/workflow-readiness";
import { Badge } from "./badge";
import { Button, buttonClassName } from "./button";
import { Card, CardHeading } from "./card";

type QuestOverviewPanelProps = {
  readonly detailError: string | null;
  readonly detailLoading: boolean;
  readonly selectedQuest: Quest | null;
  readonly selectedQuestId: string | null;
  readonly stages: readonly StageCard[];
};

type PreviewItem = {
  readonly detail: string;
  readonly title: string;
  readonly value: string;
};

function BriefItem({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 line-clamp-3 text-sm text-slate-700">{value}</p>
    </div>
  );
}

function usePreviewItems(stages: readonly StageCard[]): readonly PreviewItem[] {
  const { t } = useI18n();
  const preview = buildPreviewData(stages);

  return [
    {
      detail: preview.demand.detail || t("canvasWaitingForOutput"),
      title: t("overviewDemandPreview"),
      value: preview.demand.value || labelFromEnum(preview.demand.status),
    },
    {
      detail: preview.literature.detail || t("canvasWaitingForOutput"),
      title: t("overviewLiteraturePreview"),
      value: `${preview.literature.paperCount} ${t("overviewPapers")}`,
    },
    {
      detail: preview.idea.detail || t("canvasWaitingForOutput"),
      title: t("overviewIdeaPreview"),
      value: preview.idea.selectedIdeaTitle ? t("canvasSelectedIdea") : `${preview.idea.ideaCount} ${t("canvasIdeaCount")}`,
    },
    {
      detail: preview.experiment.detail || t("canvasWaitingForOutput"),
      title: t("overviewExperimentPreview"),
      value: preview.experiment.scriptStepCount > 0 ? `${preview.experiment.scriptStepCount} ${t("canvasPlanSteps")}` : labelFromEnum(preview.experiment.status),
    },
    {
      detail: preview.writing.detail || t("canvasWaitingForOutput"),
      title: t("overviewWritingPreview"),
      value: preview.writing.artifactCount === null ? labelFromEnum(preview.writing.status) : `${preview.writing.artifactCount} ${t("canvasArtifacts")}`,
    },
  ];
}

function downloadReviewPacket(quest: Quest, stages: readonly StageCard[]) {
  const packet = buildQuestReviewPacket(quest, stages);
  downloadTextFile({
    content: packet.content,
    filename: packet.filename,
    mimeType: "text/markdown;charset=utf-8",
  });
}

export function QuestOverviewPanel({
  detailError,
  detailLoading,
  selectedQuest,
  selectedQuestId,
  stages,
}: QuestOverviewPanelProps) {
  const { t } = useI18n();
  const progress = summarizeProgress(stages);
  const nextStage = findNextStage(stages);
  const intake = selectedQuest ? parseIntakeBrief(selectedQuest.initial_direction) : null;
  const previews = usePreviewItems(stages);
  const lastStage = stages.length > 0 ? stages[stages.length - 1] ?? null : null;
  const reviewStage = nextStage ?? stages.find((stage) => stage.agent_id === paperMeetingWriterAgentId) ?? lastStage;
  const nextStageReadiness = nextStage ? getWorkflowStageReadiness(nextStage, stages) : null;

  return (
    <Card>
      <CardHeading
        action={
          selectedQuest ? (
            <Button onClick={() => downloadReviewPacket(selectedQuest, stages)} size="sm" type="button" variant="secondary">
              {t("downloadReviewPacket")}
            </Button>
          ) : null
        }
        description={t("questOverviewDescription")}
        title={t("questOverviewTitle")}
      />
      {!selectedQuestId ? <p className="mt-4 text-sm text-slate-500">{t("questOverviewEmpty")}</p> : null}
      {detailError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{detailError}</p> : null}
      {detailLoading ? <p className="mt-4 text-sm text-slate-500">{t("loadingQuestDetail")}</p> : null}
      {selectedQuest && intake ? (
        <div className="mt-6 space-y-5">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("currentQuest")}</p>
                <h3 className="mt-1 text-base font-semibold text-slate-900">{selectedQuest.title}</h3>
                <p className="mt-2 line-clamp-3 text-sm text-slate-600">
                  {intake.direction || selectedQuest.initial_direction}
                </p>
              </div>
              <Badge tone={questTone(selectedQuest.status)}>{labelFromEnum(selectedQuest.status)}</Badge>
            </div>
            <div className="mt-4 grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
              <p>
                {t("created")} {formatDateTime(selectedQuest.created_at)}
              </p>
              <p>
                {t("updated")} {formatDateTime(selectedQuest.updated_at)}
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 min-[1400px]:grid-cols-4">
            <BriefItem label={t("overviewCompleteStages")} value={`${progress.complete}/${progress.total}`} />
            <BriefItem label={t("overviewRunningStages")} value={String(progress.running)} />
            <BriefItem label={t("overviewBlockedStages")} value={String(progress.blocked)} />
            <BriefItem label={t("overviewPendingStages")} value={String(progress.pending)} />
          </div>

          <div className="rounded-lg border border-slate-200 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("overviewNextAction")}</p>
                <p className="mt-1 font-medium text-slate-900">{nextStage ? nextStage.title : t("overviewAllStagesComplete")}</p>
                {nextStageReadiness ? <p className="mt-2 text-sm text-slate-600">{getLocalizedWorkflowReadinessReason(nextStageReadiness, t)}</p> : null}
              </div>
              {nextStage ? <Badge tone={stageTone(nextStage.status)}>{labelFromEnum(nextStage.status)}</Badge> : null}
            </div>
          </div>

          <div>
            <p className="text-sm font-semibold text-slate-900">{t("overviewIntakeBrief")}</p>
            <div className="mt-3 grid gap-3 min-[1400px]:grid-cols-2">
              <BriefItem label={t("questScenario")} value={intake.scenario || t("notAvailable")} />
              <BriefItem label={t("questTargetUser")} value={intake.targetUser || t("notAvailable")} />
              <BriefItem label={t("questTarget")} value={intake.target || t("notAvailable")} />
              <BriefItem label={t("questPainPoint")} value={intake.painPoint || t("notAvailable")} />
              <BriefItem label={t("questKnownWork")} value={intake.knownWork || t("notAvailable")} />
              <BriefItem label={t("questDataAssets")} value={intake.dataAssets || t("notAvailable")} />
              <BriefItem label={t("questMetric")} value={intake.metric || t("notAvailable")} />
              <BriefItem label={t("questExpectedOutput")} value={intake.expectedOutput || t("notAvailable")} />
              <BriefItem label={t("questOutputLanguage")} value={intake.outputLanguage || t("notAvailable")} />
            </div>
          </div>

          <div>
            <p className="text-sm font-semibold text-slate-900">{t("overviewOutputPreview")}</p>
            <div className="mt-3 grid gap-3 min-[1400px]:grid-cols-2">
              {previews.map((preview) => (
                <div className="rounded-lg border border-slate-200 bg-white p-3" key={preview.title}>
                  <p className="text-xs font-semibold text-slate-500">{preview.title}</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">{preview.value}</p>
                  <p className="mt-2 line-clamp-2 text-xs text-slate-500">{preview.detail}</p>
                </div>
              ))}
            </div>
          </div>

          <Link
            className={buttonClassName({ className: "w-full", variant: "secondary" })}
            to={reviewStage ? `/stages/${reviewStage.id}?quest=${selectedQuest.id}` : `/?quest=${selectedQuest.id}`}
          >
            {nextStage ? t("overviewOpenNextStage") : t("overviewReviewArtifacts")}
          </Link>
        </div>
      ) : null}
    </Card>
  );
}
