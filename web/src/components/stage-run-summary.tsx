import { Link } from "react-router-dom";
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
import { buttonClassName } from "./button";

function readString(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

function providerLabel(providerName: string, providerModel: string) {
  if (!providerName) {
    return "";
  }
  return providerModel ? `${providerName} · ${providerModel}` : providerName;
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
  const providerModel = readString(stage.evidence_payload, "provider_model");
  const provider = providerLabel(providerName, providerModel);
  const availabilityReason = stageRunGate
    ? getLocalizedStageRunGateReason(stageRunGate, t)
    : workflowReadiness
      ? getLocalizedWorkflowReadinessReason(workflowReadiness, t)
      : getLocalizedStageRunReason(stage, t);
  const canRun = stageRunGate?.canRun ?? workflowReadiness?.canRun ?? availability.canRun;
  const blockingStages = stageRunGate?.workflowReadiness.blockingStages ?? workflowReadiness?.blockingStages ?? [];

  return (
    <div className="mt-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={stage.confidence === "unknown" ? "gray" : "teal"}>
          {t("stageConfidence")}: {labelFromEnum(stage.confidence)}
        </Badge>
        {provider ? (
          <Badge tone="blue">
            {t("providerReadinessProvider")}: {provider}
          </Badge>
        ) : null}
      </div>
      <p className="text-sm text-slate-600">{stage.summary || t("noSummaryYet")}</p>
      <p className="text-xs text-slate-500">
        {canRun ? t("stageRunReady") : t("stageRunUnavailable")}: {availabilityReason}
      </p>
      {!canRun && blockingStages.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-slate-500">{t("stageRunOpenBlockingStage")}</span>
          {blockingStages.map((blockingStage) => (
            <Link
              className={buttonClassName({ size: "sm", variant: "secondary" })}
              key={blockingStage.id}
              to={`/stages/${blockingStage.id}?quest=${stage.quest_id}`}
            >
              {blockingStage.title}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
