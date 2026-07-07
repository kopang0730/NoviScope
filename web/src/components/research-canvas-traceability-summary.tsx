import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import {
  isHumanGateStage,
  needsHumanReview,
} from "../lib/research-canvas-data";
import { readSourceStageIds } from "../lib/source-stage-ids";
import { Badge, type BadgeTone } from "./badge";

function payloadFieldCount(payload: Readonly<Record<string, unknown>>) {
  return Object.keys(payload).length;
}

function payloadHasFields(payload: Readonly<Record<string, unknown>>) {
  return payloadFieldCount(payload) > 0;
}

function sourceStageLinkCount(stage: StageCard) {
  return Object.keys(readSourceStageIds(stage.output_payload)).length;
}

function integrityTone({
  blockedCount,
  evidenceStageCount,
  pendingReviewCount,
  rejectedGateCount,
}: {
  readonly blockedCount: number;
  readonly evidenceStageCount: number;
  readonly pendingReviewCount: number;
  readonly rejectedGateCount: number;
}): BadgeTone {
  if (rejectedGateCount > 0 || blockedCount > 0) {
    return "red";
  }
  if (pendingReviewCount > 0 || evidenceStageCount === 0) {
    return "amber";
  }
  return "green";
}

function MetricCard({
  caption,
  label,
  value,
}: {
  readonly caption: string;
  readonly label: string;
  readonly value: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-950">{value}</p>
      <p className="mt-1 text-xs leading-5 text-slate-600">{caption}</p>
    </div>
  );
}

export function ResearchCanvasTraceabilitySummary({ stages }: { readonly stages: readonly StageCard[] }) {
  const { t } = useI18n();
  const gateStages = stages.filter(isHumanGateStage);
  const evidenceStageCount = stages.filter((stage) => payloadHasFields(stage.evidence_payload)).length;
  const outputStageCount = stages.filter((stage) => payloadHasFields(stage.output_payload)).length;
  const totalEvidenceFields = stages.reduce((count, stage) => count + payloadFieldCount(stage.evidence_payload), 0);
  const totalOutputFields = stages.reduce((count, stage) => count + payloadFieldCount(stage.output_payload), 0);
  const sourceLinkCount = stages.reduce((count, stage) => count + sourceStageLinkCount(stage), 0);
  const approvedGateCount = gateStages.filter((stage) => stage.human_approved === true).length;
  const pendingReviewCount = gateStages.filter(needsHumanReview).length;
  const rejectedGateCount = gateStages.filter((stage) => stage.human_approved === false).length;
  const blockedCount = stages.filter((stage) => stage.status === "blocked").length;
  const statusTone = integrityTone({
    blockedCount,
    evidenceStageCount,
    pendingReviewCount,
    rejectedGateCount,
  });
  const statusLabel =
    rejectedGateCount > 0
      ? t("canvasTraceabilityRejected")
      : blockedCount > 0
        ? t("canvasTraceabilityBlocked")
        : pendingReviewCount > 0
          ? t("canvasTraceabilityReviewNeeded")
          : evidenceStageCount === 0
            ? t("canvasTraceabilityEvidenceMissing")
            : t("canvasTraceabilityReady");

  return (
    <section className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-950">{t("canvasTraceabilitySummaryTitle")}</p>
          <p className="mt-1 text-sm leading-6 text-slate-600">{t("canvasTraceabilitySummaryDescription")}</p>
        </div>
        <Badge tone={statusTone}>{statusLabel}</Badge>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 2xl:grid-cols-4">
        <MetricCard
          caption={`${totalEvidenceFields} ${t("canvasEvidenceFields")}`}
          label={t("canvasTraceabilityEvidenceCoverage")}
          value={`${evidenceStageCount}/${stages.length}`}
        />
        <MetricCard
          caption={`${totalOutputFields} ${t("canvasOutputFields")}`}
          label={t("canvasTraceabilityOutputCoverage")}
          value={`${outputStageCount}/${stages.length}`}
        />
        <MetricCard
          caption={`${sourceLinkCount} ${t("sourceStages")}`}
          label={t("canvasTraceabilitySourceLinks")}
          value={String(sourceLinkCount)}
        />
        <MetricCard
          caption={`${pendingReviewCount} ${t("stageReviewPending")} · ${rejectedGateCount} ${t("stageReviewRejected")}`}
          label={t("canvasTraceabilityHumanGates")}
          value={`${approvedGateCount}/${gateStages.length}`}
        />
      </div>
    </section>
  );
}
