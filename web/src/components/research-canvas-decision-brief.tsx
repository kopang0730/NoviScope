import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import {
  buildStageDetails,
  isHumanGateStage,
  needsHumanReview,
  phaseKeyForAgent,
} from "../lib/research-canvas-data";
import { getLocalizedStageRunGateReason, getStageRunGate } from "../lib/stage-run-gate";
import { stageTone } from "../lib/status-tones";
import { Badge, type BadgeTone } from "./badge";

type EvidencePreview = {
  readonly detail: string;
  readonly phaseLabel: string;
  readonly stage: StageCard;
};

function reviewTone(rejectedCount: number, pendingReviewCount: number): BadgeTone {
  if (rejectedCount > 0) {
    return "red";
  }
  if (pendingReviewCount > 0) {
    return "amber";
  }
  return "green";
}

function buildEvidencePreviews(
  stages: readonly StageCard[],
  t: ReturnType<typeof useI18n>["t"],
): readonly EvidencePreview[] {
  return stages
    .filter((stage) => stage.status !== "pending")
    .map((stage) => {
      const details = buildStageDetails(stage, t);
      const lastDetail = details[details.length - 1];
      return {
        detail: stage.summary || lastDetail?.value || "",
        phaseLabel: t(phaseKeyForAgent(stage.agent_id)),
        stage,
      };
    })
    .filter((preview) => preview.detail.trim().length > 0)
    .slice(0, 4);
}

export function ResearchCanvasDecisionBrief({
  nextActionStage,
  providerReadinessData,
  stages,
}: {
  readonly nextActionStage: StageCard | null;
  readonly providerReadinessData: ProviderReadinessData;
  readonly stages: readonly StageCard[];
}) {
  const { t } = useI18n();
  const gateStages = stages.filter(isHumanGateStage);
  const approvedCount = gateStages.filter((stage) => stage.human_approved === true).length;
  const rejectedStages = gateStages.filter((stage) => stage.human_approved === false);
  const reviewStages = stages.filter(needsHumanReview);
  const evidencePreviews = buildEvidencePreviews(stages, t);
  const nextActionGate = nextActionStage
    ? getStageRunGate({ providerReadinessData, stage: nextActionStage, stages })
    : null;
  const nextActionReason = nextActionGate
    ? getLocalizedStageRunGateReason(nextActionGate, t)
    : t("canvasNoNextAction");
  const rejectedStage = rejectedStages[0] ?? null;
  const reviewStage = reviewStages[0] ?? null;
  const reviewBadge = rejectedStage
    ? t("stageReviewRejected")
    : reviewStage
      ? t("stageReviewPending")
      : t("stageReviewApproved");
  const reviewSummary = rejectedStage
    ? rejectedStage.title
    : reviewStage
      ? reviewStage.title
      : `${approvedCount}/${gateStages.length} ${t("canvasDecisionApprovedCount")}`;

  return (
    <section className="grid gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <div className="rounded-lg border border-teal-200 bg-teal-50/70 p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-teal-950">{t("canvasDecisionBriefTitle")}</p>
            <p className="mt-1 text-sm leading-6 text-teal-800">{t("canvasDecisionBriefDescription")}</p>
          </div>
          <Badge tone={nextActionStage ? stageTone(nextActionStage.status) : "gray"}>
            {nextActionStage ? t("canvasNextAction") : t("canvasNoNextAction")}
          </Badge>
        </div>

        <div className="mt-4 grid gap-3 min-[1600px]:grid-cols-3">
          <div className="rounded-md border border-teal-200 bg-white/80 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-teal-700">
              {t("canvasDecisionNextActionLabel")}
            </p>
            <p className="mt-1 line-clamp-2 text-sm font-semibold text-slate-950">
              {nextActionStage?.title ?? t("canvasNoNextAction")}
            </p>
            <p className="mt-2 line-clamp-3 text-xs leading-5 text-slate-600">{nextActionReason}</p>
          </div>

          <div className="rounded-md border border-teal-200 bg-white/80 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-teal-700">
              {t("canvasDecisionReviewGateLabel")}
            </p>
            <div className="mt-1">
              <Badge tone={reviewTone(rejectedStages.length, reviewStages.length)}>{reviewBadge}</Badge>
            </div>
            <p className="mt-2 line-clamp-2 text-xs font-medium leading-5 text-slate-700">{reviewSummary}</p>
            <p className="mt-1 text-xs leading-5 text-slate-600">{t("canvasDecisionReviewGateDescription")}</p>
          </div>

          <div className="rounded-md border border-teal-200 bg-white/80 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-teal-700">
              {t("canvasDecisionEvidenceLabel")}
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-950">
              {evidencePreviews.length > 0
                ? `${evidencePreviews.length} ${t("canvasDecisionEvidenceReady")}`
                : t("canvasDecisionEvidenceWaiting")}
            </p>
            <p className="mt-2 text-xs leading-5 text-slate-600">{t("canvasDecisionEvidenceDescription")}</p>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm font-semibold text-slate-950">{t("canvasDecisionEvidencePreviewTitle")}</p>
        <div className="mt-3 grid gap-2">
          {evidencePreviews.length > 0 ? (
            evidencePreviews.map((preview) => (
              <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2" key={preview.stage.id}>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={stageTone(preview.stage.status)}>{labelFromEnum(preview.stage.status)}</Badge>
                  <span className="text-xs font-semibold text-slate-700">{preview.phaseLabel}</span>
                </div>
                <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-600">{preview.detail}</p>
              </div>
            ))
          ) : (
            <p className="rounded-md border border-dashed border-slate-300 px-3 py-3 text-xs text-slate-500">
              {t("canvasDecisionNoEvidencePreview")}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
