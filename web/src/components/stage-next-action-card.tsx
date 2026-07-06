import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { runStage } from "../api/quests";
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
import { Button, buttonClassName } from "./button";
import { Card, CardHeading } from "./card";

function findNextWorkflowStage(stage: StageCard, stages: readonly StageCard[]) {
  const stageIndex = stages.findIndex((candidate) => candidate.id === stage.id);
  if (stageIndex < 0) {
    return null;
  }

  return stages[stageIndex + 1] ?? null;
}

export function StageNextActionCard({
  onStageChange,
  providerReadinessData,
  stage,
  stages,
}: {
  readonly onStageChange?: (stage: StageCard) => void;
  readonly providerReadinessData: ProviderReadinessData;
  readonly stage: StageCard;
  readonly stages: readonly StageCard[];
}) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [runError, setRunError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

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

  async function handleRunNextStage(stageToRun: StageCard) {
    setRunError(null);
    setRunning(true);

    try {
      const updatedStage = await runStage(stageToRun.id);
      onStageChange?.(updatedStage);
      navigate(`/stages/${updatedStage.id}?quest=${updatedStage.quest_id}`);
    } catch (error) {
      if (error instanceof Error) {
        setRunError(getErrorMessage(error));
        return;
      }
      throw error;
    } finally {
      setRunning(false);
    }
  }

  return (
    <Card className="border-teal-200 bg-teal-50/50">
      <CardHeading
        action={
          <div className="flex flex-wrap gap-2">
            {nextGate.canRun ? (
              <Button loading={running} onClick={() => void handleRunNextStage(nextStage)} size="sm" type="button">
                {t("stageNextActionRunNextStage")}
              </Button>
            ) : null}
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

        {runError ? (
          <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {runError}
          </p>
        ) : null}

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
