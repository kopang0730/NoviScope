import { Link } from "react-router-dom";
import type { Quest, StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import type { CanvasDetail } from "../lib/research-canvas-data";
import {
  getLocalizedStageRunGateReason,
  type StageRunGate,
} from "../lib/stage-run-gate";
import { stageTone } from "../lib/status-tones";
import { Badge, type BadgeTone } from "./badge";
import { Button, buttonClassName } from "./button";

function reviewTone(stage: StageCard): BadgeTone {
  if (stage.human_approved === true) {
    return "green";
  }
  if (stage.human_approved === false) {
    return "red";
  }
  return "amber";
}

function reviewLabel(stage: StageCard, t: ReturnType<typeof useI18n>["t"]) {
  if (stage.human_approved === true) {
    return t("stageReviewApproved");
  }
  if (stage.human_approved === false) {
    return t("stageReviewRejected");
  }
  return t("stageReviewPending");
}

export function ResearchCanvasInspector({
  details,
  onRunStage,
  runningStageId,
  selectedQuest,
  stage,
  stageRunGate,
}: {
  readonly details: readonly CanvasDetail[];
  readonly onRunStage: (stageId: string) => void;
  readonly runningStageId: string | null;
  readonly selectedQuest: Quest;
  readonly stage: StageCard;
  readonly stageRunGate: StageRunGate;
}) {
  const { t } = useI18n();
  const runReason = getLocalizedStageRunGateReason(stageRunGate, t);

  return (
    <aside className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("canvasInspectorTitle")}</p>
          <h3 className="mt-1 text-base font-semibold text-slate-950">{stage.title}</h3>
          <p className="mt-1 break-all text-xs text-slate-500">{stage.agent_id}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge>
          <Badge tone={reviewTone(stage)}>{reviewLabel(stage, t)}</Badge>
          <Badge tone="gray">{labelFromEnum(stage.confidence)}</Badge>
        </div>
      </div>

      <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t("stageRunState")}</p>
        <p className="mt-1 text-xs leading-5 text-slate-700">{runReason}</p>
      </div>

      <div className="mt-4">
        <p className="text-xs font-semibold text-slate-900">{t("canvasStageEvidenceTrail")}</p>
        <div className="mt-2 grid gap-2">
          {details.length > 0 ? (
            details.map((detail) => (
              <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2" key={`${stage.id}-${detail.label}`}>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{detail.label}</p>
                <p className="mt-1 text-xs leading-5 text-slate-700">{detail.value}</p>
              </div>
            ))
          ) : (
            <p className="rounded-md border border-dashed border-slate-300 px-3 py-3 text-xs text-slate-500">
              {t("canvasNoEvidenceYet")}
            </p>
          )}
        </div>
      </div>

      <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t("reviewNotes")}</p>
        <p className="mt-1 text-xs leading-5 text-slate-700">
          {stage.review_notes || t("canvasReviewNotRecorded")}
        </p>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {stageRunGate.canRun ? (
          <Button loading={runningStageId === stage.id} onClick={() => onRunStage(stage.id)} size="sm">
            {t("runStage")}
          </Button>
        ) : null}
        <Link className={buttonClassName({ size: "sm", variant: "secondary" })} to={`/stages/${stage.id}?quest=${selectedQuest.id}`}>
          {t("open")}
        </Link>
      </div>

      <p className="mt-4 text-xs text-slate-500">
        {t("updated")} {formatDateTime(stage.updated_at)}
      </p>
    </aside>
  );
}
