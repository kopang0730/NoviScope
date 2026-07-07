import { Link } from "react-router-dom";
import type { Quest, StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import { findNextActionStage, needsHumanReview } from "../lib/research-canvas-data";
import {
  getLocalizedStageRunGateReason,
  getStageRunGate,
  type StageRunGate,
} from "../lib/stage-run-gate";
import { stageTone } from "../lib/status-tones";
import { Badge, type BadgeTone } from "./badge";
import { Button, buttonClassName } from "./button";

type QuestNextActionState =
  | "blocked"
  | "complete"
  | "empty"
  | "review"
  | "runnable"
  | "running";

type QuestNextActionCardProps = {
  readonly onRunStage: (stageId: string) => void;
  readonly providerReadinessData: ProviderReadinessData;
  readonly quest: Quest;
  readonly runningStageId: string | null;
  readonly stages: readonly StageCard[];
};

function outputFieldCount(stage: StageCard) {
  return Object.keys(stage.output_payload).length;
}

function evidenceFieldCount(stage: StageCard) {
  return Object.keys(stage.evidence_payload).length;
}

function actionState(stage: StageCard | null, gate: StageRunGate | null): QuestNextActionState {
  if (!stage) {
    return "complete";
  }
  if (stage.status === "running") {
    return "running";
  }
  if (needsHumanReview(stage)) {
    return "review";
  }
  if (gate?.canRun) {
    return "runnable";
  }
  return "blocked";
}

function stateTone(state: QuestNextActionState): BadgeTone {
  if (state === "complete") {
    return "green";
  }
  if (state === "runnable") {
    return "teal";
  }
  if (state === "blocked") {
    return "red";
  }
  if (state === "empty") {
    return "gray";
  }
  return "amber";
}

export function QuestNextActionCard({
  onRunStage,
  providerReadinessData,
  quest,
  runningStageId,
  stages,
}: QuestNextActionCardProps) {
  const { t } = useI18n();
  const nextStage = findNextActionStage(stages, providerReadinessData);
  const nextGate = nextStage ? getStageRunGate({ providerReadinessData, stage: nextStage, stages }) : null;
  const state = stages.length === 0 ? "empty" : actionState(nextStage, nextGate);
  const canvasHref = `/canvas?quest=${quest.id}`;

  if (state === "empty") {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t("questNextActionTitle")}
            </p>
            <p className="mt-1 font-medium text-slate-900">{t("questNextActionEmptyTitle")}</p>
            <p className="mt-2 text-sm text-slate-600">{t("questNextActionEmptyDescription")}</p>
          </div>
          <Badge tone="gray">{t("canvasNoNextAction")}</Badge>
        </div>
      </div>
    );
  }

  if (!nextStage) {
    return (
      <div className="rounded-lg border border-emerald-200 bg-emerald-50/70 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
              {t("questNextActionTitle")}
            </p>
            <p className="mt-1 font-medium text-slate-900">{t("questNextActionCompleteTitle")}</p>
            <p className="mt-2 text-sm text-slate-600">{t("questNextActionCompleteDescription")}</p>
          </div>
          <Badge tone="green">{t("overviewAllStagesComplete")}</Badge>
        </div>
        <Link className={buttonClassName({ className: "mt-4", size: "sm", variant: "secondary" })} to={canvasHref}>
          {t("stageNextActionOpenCanvas")}
        </Link>
      </div>
    );
  }

  const stageHref = `/stages/${nextStage.id}?quest=${quest.id}`;
  const providerLabel = nextGate?.providerReadiness.providerName
    ? `${nextGate.providerReadiness.providerName}${
        nextGate.providerReadiness.modelName ? ` · ${nextGate.providerReadiness.modelName}` : ""
      }`
    : t("notAvailable");

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t("questNextActionTitle")}
          </p>
          <p className="mt-1 break-words font-medium text-slate-900">{nextStage.title}</p>
          <p className="mt-2 text-sm text-slate-600">
            {nextGate ? getLocalizedStageRunGateReason(nextGate, t) : t("workflowReadinessStatusComplete")}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Badge tone={stageTone(nextStage.status)}>{labelFromEnum(nextStage.status)}</Badge>
          <Badge tone={stateTone(state)}>{t(`questNextActionState_${state}`)}</Badge>
        </div>
      </div>

      <div className="mt-4 grid gap-3 text-xs text-slate-500 sm:grid-cols-2 xl:grid-cols-4">
        <p>
          <span className="font-semibold text-slate-700">{t("questNextActionProviderRoute")}:</span>{" "}
          {providerLabel}
        </p>
        <p>
          <span className="font-semibold text-slate-700">{t("stageHumanApproval")}:</span>{" "}
          {nextStage.human_approved === true
            ? t("stageReviewApproved")
            : nextStage.human_approved === false
              ? t("stageReviewRejected")
              : t("stageReviewPending")}
        </p>
        <p>
          <span className="font-semibold text-slate-700">{t("canvasOutputFields")}:</span>{" "}
          {outputFieldCount(nextStage)}
        </p>
        <p>
          <span className="font-semibold text-slate-700">{t("canvasEvidenceFields")}:</span>{" "}
          {evidenceFieldCount(nextStage)}
        </p>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {nextGate?.canRun ? (
          <Button loading={runningStageId === nextStage.id} onClick={() => onRunStage(nextStage.id)} size="sm">
            {t("runStage")}
          </Button>
        ) : null}
        <Link className={buttonClassName({ size: "sm", variant: "secondary" })} to={stageHref}>
          {t("questNextActionOpenStage")}
        </Link>
        <Link className={buttonClassName({ size: "sm", variant: "ghost" })} to={canvasHref}>
          {t("stageNextActionOpenCanvas")}
        </Link>
      </div>

      <p className="mt-3 text-xs text-slate-500">
        {t("updated")}: {formatDateTime(nextStage.updated_at)}
      </p>
    </div>
  );
}
