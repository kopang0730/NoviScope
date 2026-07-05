import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import {
  getLocalizedStageRunGateReason,
  type StageRunGate,
} from "../lib/stage-run-gate";
import { getLocalizedStageRunReason } from "../lib/stage-run-text";
import { getStageRunAvailability } from "../lib/stages";
import {
  getLocalizedWorkflowReadinessReason,
  type WorkflowStageReadiness,
} from "../lib/workflow-readiness";
import { Badge } from "./badge";

function readString(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

export function StageRunSummary({
  stage,
  stageRunGate,
  workflowReadiness,
}: {
  readonly stage: StageCard;
  readonly stageRunGate?: StageRunGate;
  readonly workflowReadiness?: WorkflowStageReadiness;
}) {
  const { t } = useI18n();
  const availability = getStageRunAvailability(stage);
  const providerName = readString(stage.evidence_payload, "provider_name");
  const availabilityReason = stageRunGate
    ? getLocalizedStageRunGateReason(stageRunGate, t)
    : workflowReadiness
      ? getLocalizedWorkflowReadinessReason(workflowReadiness, t)
      : getLocalizedStageRunReason(stage, t);
  const canRun = stageRunGate?.canRun ?? workflowReadiness?.canRun ?? availability.canRun;

  return (
    <div className="mt-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={stage.confidence === "unknown" ? "gray" : "teal"}>
          {t("stageConfidence")}: {labelFromEnum(stage.confidence)}
        </Badge>
        {providerName ? <Badge tone="blue">{providerName}</Badge> : null}
      </div>
      <p className="text-sm text-slate-600">{stage.summary || t("noSummaryYet")}</p>
      <p className="text-xs text-slate-500">
        {canRun ? t("stageRunReady") : t("stageRunUnavailable")}: {availabilityReason}
      </p>
    </div>
  );
}
