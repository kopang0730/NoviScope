import { useEffect, useMemo, useState } from "react";
import { getErrorMessage } from "../api/client";
import { getWorkflowAutopilotPlan } from "../api/quests";
import type { AutopilotPlan, AutopilotStatus, Quest, StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { Badge } from "./badge";
import { Button } from "./button";

const autopilotTone: Record<AutopilotStatus, "amber" | "blue" | "gray" | "green" | "red" | "teal"> = {
  blocked: "red",
  complete: "green",
  needs_configuration: "amber",
  ready_to_run: "teal",
  waiting_for_human_review: "blue",
};

function stageSignature(stages: readonly StageCard[]) {
  return stages
    .map((stage) => `${stage.id}:${stage.status}:${stage.human_approved ?? "pending"}:${stage.updated_at}`)
    .join("|");
}

export function WorkflowAutopilotCard({
  onRunStage,
  quest,
  runningStageId,
  stages,
}: {
  readonly onRunStage: (stageId: string) => void;
  readonly quest: Quest;
  readonly runningStageId: string | null;
  readonly stages: readonly StageCard[];
}) {
  const { t } = useI18n();
  const [plan, setPlan] = useState<AutopilotPlan | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const signature = useMemo(() => stageSignature(stages), [stages]);

  useEffect(() => {
    let isCurrent = true;
    setError("");
    setLoading(true);

    void getWorkflowAutopilotPlan(quest.id)
      .then((nextPlan) => {
        if (isCurrent) {
          setPlan(nextPlan);
        }
      })
      .catch((caught: unknown) => {
        if (caught instanceof Error && isCurrent) {
          setError(getErrorMessage(caught));
          return;
        }
        throw caught;
      })
      .finally(() => {
        if (isCurrent) {
          setLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [quest.id, signature]);

  const runnableStageId = plan?.next_stage_id ?? null;
  const stageIsRunning = runnableStageId !== null && runningStageId === runnableStageId;

  return (
    <div className="border-l-4 border-teal-400 bg-teal-50/60 px-4 py-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-900">{t("autopilotPlanTitle")}</h3>
            {plan ? <Badge tone={autopilotTone[plan.status]}>{labelFromEnum(plan.status)}</Badge> : null}
          </div>
          <p className="mt-1 text-sm text-slate-700">
            {loading ? t("autopilotPlanLoading") : plan?.summary ?? t("autopilotPlanUnavailable")}
          </p>
          {plan?.stop_stage_title ? (
            <p className="mt-1 text-xs text-slate-500">
              {t("autopilotPlanStop")}: {plan.stop_stage_title}
            </p>
          ) : null}
          {error ? <p className="mt-2 text-sm text-rose-700">{error}</p> : null}
        </div>
        {runnableStageId ? (
          <Button loading={stageIsRunning} onClick={() => onRunStage(runnableStageId)} size="sm" type="button">
            {t("autopilotRunNext")}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
