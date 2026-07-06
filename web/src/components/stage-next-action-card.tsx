import { Link } from "react-router-dom";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import {
  getLocalizedStageRunGateReason,
  getStageRunGate,
} from "../lib/stage-run-gate";
import { stageTone } from "../lib/status-tones";
import { Badge } from "./badge";
import { buttonClassName } from "./button";
import { Card, CardHeading } from "./card";

function findNextWorkflowStage(stage: StageCard, stages: readonly StageCard[]) {
  const stageIndex = stages.findIndex((candidate) => candidate.id === stage.id);
  if (stageIndex < 0) {
    return null;
  }

  return stages[stageIndex + 1] ?? null;
}

export function StageNextActionCard({
  providerReadinessData,
  stage,
  stages,
}: {
  readonly providerReadinessData: ProviderReadinessData;
  readonly stage: StageCard;
  readonly stages: readonly StageCard[];
}) {
  const { t } = useI18n();

  if (stage.status !== "complete") {
    return null;
  }

  const nextStage = findNextWorkflowStage(stage, stages);
  const canvasHref = `/canvas?quest=${stage.quest_id}`;

  if (!nextStage) {
    return (
      <Card className="border-emerald-200 bg-emerald-50/50">
        <CardHeading
          action={
            <Link className={buttonClassName({ size: "sm", variant: "secondary" })} to={canvasHref}>
              {t("stageNextActionOpenCanvas")}
            </Link>
          }
          description={t("stageNextActionCompleteDescription")}
          title={t("stageNextActionCompleteTitle")}
        />
      </Card>
    );
  }

  const nextGate = getStageRunGate({
    providerReadinessData,
    stage: nextStage,
    stages,
  });
  const nextStageHref = `/stages/${nextStage.id}?quest=${nextStage.quest_id}`;

  return (
    <Card className="border-teal-200 bg-teal-50/50">
      <CardHeading
        action={
          <div className="flex flex-wrap gap-2">
            <Link className={buttonClassName({ size: "sm", variant: "primary" })} to={nextStageHref}>
              {t("stageNextActionOpenNextStage")}
            </Link>
            <Link className={buttonClassName({ size: "sm", variant: "secondary" })} to={canvasHref}>
              {t("stageNextActionOpenCanvas")}
            </Link>
          </div>
        }
        description={t("stageNextActionDescription")}
        title={t("stageNextActionTitle")}
      />

      <div className="mt-4 rounded-lg border border-teal-200 bg-white p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
              {t("stageNextActionNextStage")}
            </p>
            <h3 className="mt-1 text-base font-semibold text-slate-950">{nextStage.title}</h3>
            <p className="mt-2 text-sm text-slate-600">{getLocalizedStageRunGateReason(nextGate, t)}</p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <Badge tone={stageTone(nextStage.status)}>{labelFromEnum(nextStage.status)}</Badge>
            <Badge tone={nextGate.canRun ? "teal" : "amber"}>
              {nextGate.canRun ? t("stageNextActionRunnable") : t("stageNextActionBlocked")}
            </Badge>
          </div>
        </div>

        <div className="mt-4 grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
          <p>
            {t("stageDetailAgentId")}: {nextStage.agent_id}
          </p>
          <p>
            {t("updated")}: {formatDateTime(nextStage.updated_at)}
          </p>
        </div>
      </div>
    </Card>
  );
}
