import { Link } from "react-router-dom";
import type { Quest, StageCard, StageStatus } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { getLocalizedStageRunReason } from "../lib/stage-run-text";
import { canRunStage } from "../lib/stages";
import { stageTone } from "../lib/status-tones";
import { Badge } from "./badge";
import { Button, buttonClassName } from "./button";

export type CanvasDetail = {
  readonly label: string;
  readonly value: string;
};

function statusBorderClassName(status: StageStatus) {
  if (status === "complete") {
    return "border-emerald-300 bg-emerald-50/60";
  }
  if (status === "blocked") {
    return "border-rose-300 bg-rose-50/70";
  }
  if (status === "running") {
    return "border-amber-300 bg-amber-50/70";
  }
  return "border-slate-300 bg-white";
}

function connectorClassName(status: StageStatus) {
  if (status === "complete") {
    return "bg-emerald-300 text-emerald-600";
  }
  if (status === "blocked") {
    return "bg-rose-300 text-rose-600";
  }
  return "bg-slate-300 text-slate-400";
}

function buildStageSignal(stage: StageCard, t: ReturnType<typeof useI18n>["t"]) {
  if (stage.human_approved === true) {
    return t("canvasGateApproved");
  }
  if (stage.human_approved === false) {
    return t("canvasGateRejected");
  }
  if (stage.status === "complete" && (stage.agent_id === "demand_validator" || stage.agent_id === "idea_generator")) {
    return t("humanReviewRequired");
  }
  if (canRunStage(stage)) {
    return t("canvasReadyToRun");
  }
  if (stage.status === "complete") {
    return t("canvasOutputReady");
  }
  if (stage.status === "blocked") {
    return t("canvasBlocked");
  }
  return t("canvasWaitingForOutput");
}

type CanvasStageNodeProps = {
  readonly details: readonly CanvasDetail[];
  readonly index: number;
  readonly isNextAction: boolean;
  readonly onRunStage: (stageId: string) => void;
  readonly phaseLabel: string;
  readonly runningStageId: string | null;
  readonly selectedQuest: Quest;
  readonly stage: StageCard;
  readonly total: number;
};

export function CanvasStageNode({
  details,
  index,
  isNextAction,
  onRunStage,
  phaseLabel,
  runningStageId,
  selectedQuest,
  stage,
  total,
}: CanvasStageNodeProps) {
  const { t } = useI18n();
  const connectorClass = connectorClassName(stage.status);
  const signal = buildStageSignal(stage, t);
  const runReason = getLocalizedStageRunReason(stage, t);

  return (
    <div className="relative">
      {index < total - 1 ? (
        <div className="absolute left-full top-12 hidden h-px w-3 lg:block" aria-hidden="true">
          <div className={["h-px w-full", connectorClass].join(" ")} />
          <span className={["absolute -right-1 -top-2 text-xs", connectorClass].join(" ")}>&gt;</span>
        </div>
      ) : null}

      <article
        className={[
          "flex min-h-[380px] flex-col rounded-lg border p-4 shadow-sm transition",
          statusBorderClassName(stage.status),
          isNextAction ? "ring-2 ring-teal-400 ring-offset-2" : "",
        ].join(" ")}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-teal-200 bg-white text-sm font-semibold text-teal-700">
                {index + 1}
              </div>
              <p className="truncate text-xs font-semibold text-teal-700">{phaseLabel}</p>
            </div>
          </div>
          <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge>
        </div>

        <div className="mt-4 min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{stage.agent_id}</p>
          <h3 className="mt-1 line-clamp-2 text-sm font-semibold text-slate-950">{stage.title}</h3>
          <p className="mt-2 line-clamp-3 text-xs text-slate-600">{stage.summary || t("noSummaryYet")}</p>
        </div>

        <div className="mt-4 grid gap-2">
          {isNextAction ? (
            <div className="rounded-md border border-teal-200 bg-teal-50 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-teal-700">{t("canvasNextAction")}</p>
              <p className="mt-1 line-clamp-2 text-xs font-medium text-teal-900">{runReason}</p>
            </div>
          ) : null}

          <div className="rounded-md border border-white/70 bg-white/80 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t("canvasReviewGate")}</p>
            <p className="mt-1 line-clamp-2 text-xs font-medium text-slate-800">{signal}</p>
          </div>

          <div className="rounded-md border border-white/70 bg-white/80 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t("stageRunState")}</p>
            <p className="mt-1 line-clamp-2 text-xs text-slate-700">{runReason}</p>
          </div>

          <div className="rounded-md border border-white/70 bg-white/80 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t("stageConfidence")}</p>
            <p className="mt-1 text-xs text-slate-700">{labelFromEnum(stage.confidence)}</p>
          </div>
        </div>

        <div className="mt-3 grid gap-2">
          {details.length > 0 ? (
            details.map((detail) => (
              <div className="rounded-md bg-white/80 px-3 py-2" key={`${stage.id}-${detail.label}`}>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{detail.label}</p>
                <p className="mt-1 line-clamp-2 text-xs text-slate-700">{detail.value}</p>
              </div>
            ))
          ) : (
            <p className="rounded-md border border-dashed border-slate-200 bg-white/70 px-3 py-2 text-xs text-slate-500">
              {t("canvasWaitingForOutput")}
            </p>
          )}
        </div>

        <div className="mt-auto flex flex-wrap items-center gap-2 pt-4">
          {canRunStage(stage) ? (
            <Button loading={runningStageId === stage.id} onClick={() => onRunStage(stage.id)} size="sm">
              {t("runStage")}
            </Button>
          ) : null}
          <Link className={buttonClassName({ size: "sm", variant: "secondary" })} to={`/stages/${stage.id}?quest=${selectedQuest.id}`}>
            {t("open")}
          </Link>
        </div>
      </article>
    </div>
  );
}
