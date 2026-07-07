import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { getQuest, getQuestStages, runStage } from "../api/quests";
import { getErrorMessage } from "../api/client";
import type { Quest, StageCard, StageStatus } from "../api/types";
import { useAuth } from "../auth/auth-context";
import { Badge } from "../components/badge";
import { Button, buttonClassName } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { StageClaimSafetyCard } from "../components/stage-claim-safety-card";
import { StageProviderReadinessCard } from "../components/stage-provider-readiness";
import { StageEditor } from "../components/stage-editor";
import { StageNextActionCard } from "../components/stage-next-action-card";
import { StageOutputPanel } from "../components/stage-output-summary";
import { StageReviewGateCard } from "../components/stage-review-gate-card";
import { useI18n } from "../i18n/i18n-context";
import { downloadTextFile } from "../lib/download-file";
import { formatDateTime, labelFromEnum } from "../lib/format";
import { useProviderReadinessData } from "../lib/provider-readiness-data";
import {
  getLocalizedStageRunGateReason,
  getStageRunGate,
} from "../lib/stage-run-gate";
import {
  buildStageReviewPacketFilename,
  buildStageReviewPacketMarkdown,
} from "../lib/stage-review-packet";

function stageTone(status: StageStatus) {
  if (status === "complete") {
    return "green";
  }
  if (status === "running") {
    return "amber";
  }
  if (status === "blocked") {
    return "red";
  }
  return "gray";
}

export function StageDetailPage() {
  const { stageId } = useParams();
  const [searchParams] = useSearchParams();
  const { authReady, currentUser } = useAuth();
  const { t } = useI18n();
  const questId = searchParams.get("quest");

  const [quest, setQuest] = useState<Quest | null>(null);
  const [stage, setStage] = useState<StageCard | null>(null);
  const [workflowStages, setWorkflowStages] = useState<readonly StageCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [runningStage, setRunningStage] = useState(false);
  const providerReadinessData = useProviderReadinessData();

  useEffect(() => {
    if (!stageId || !questId || !currentUser) {
      setQuest(null);
      setStage(null);
      setWorkflowStages([]);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setLoadError(null);

    void Promise.all([getQuest(questId), getQuestStages(questId)])
      .then(([nextQuest, stages]) => {
        if (!active) {
          return;
        }

        const nextStage = stages.find((candidate) => candidate.id === stageId);
        if (!nextStage) {
          throw new Error("Stage not found in the selected quest.");
        }

        setQuest(nextQuest);
        setStage(nextStage);
        setWorkflowStages(stages);
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        if (error instanceof Error) {
          setLoadError(getErrorMessage(error));
          return;
        }
        throw error;
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [currentUser, questId, stageId]);

  const workflowBackLink = useMemo(() => (questId ? `/?quest=${questId}` : "/"), [questId]);
  const stageRunGate = stage
    ? getStageRunGate({ providerReadinessData, stage, stages: workflowStages })
    : null;

  function handleStageChange(nextStage: StageCard) {
    setStage(nextStage);
    setWorkflowStages((currentStages) =>
      currentStages.map((candidate) => (candidate.id === nextStage.id ? nextStage : candidate)),
    );
  }

  async function handleRunStage() {
    if (!stageId) {
      return;
    }

    setRunningStage(true);
    setRunError(null);
    setSuccessMessage(null);

    try {
      const updatedStage = await runStage(stageId);
      handleStageChange(updatedStage);
      setSuccessMessage(updatedStage.status === "blocked" ? t("stageRunBlocked") : t("stageRunComplete"));
    } catch (error) {
      if (error instanceof Error) {
        setRunError(getErrorMessage(error));
      } else {
        throw error;
      }
    } finally {
      setRunningStage(false);
    }
  }

  function handleDownloadReviewPacket(currentStage: StageCard) {
    downloadTextFile({
      content: buildStageReviewPacketMarkdown(currentStage, t),
      filename: buildStageReviewPacketFilename(currentStage),
      mimeType: "text/markdown;charset=utf-8",
    });
  }

  if (!questId) {
    return (
      <Card>
        <CardHeading description={t("stageDetailMissingQuestDescription")} title={t("stageDetailTitle")} />
        <p className="mt-4 text-sm text-slate-600">{t("stageDetailMissingQuestBody")}</p>
      </Card>
    );
  }

  if (!currentUser && authReady) {
    return (
      <Card>
        <CardHeading description={t("stageDetailSignInDescription")} title={t("stageDetailTitle")} />
        <Link className={buttonClassName({ variant: "primary" })} to="/login">
          {t("stageDetailGoToLogin")}
        </Link>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm text-slate-500">{t("stageEditorEyebrow")}</p>
            <h1 className="mt-1 text-xl font-semibold text-slate-900">{stage?.title ?? t("stageDetailFallbackTitle")}</h1>
            {quest ? <p className="mt-2 text-sm text-slate-600">{quest.title}</p> : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {stage ? <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge> : null}
            {stage && stageRunGate?.canRun ? (
              <Button loading={runningStage} onClick={() => void handleRunStage()} size="sm">
                {t("runStage")}
              </Button>
            ) : null}
            {stage ? (
              <Button onClick={() => handleDownloadReviewPacket(stage)} size="sm" type="button" variant="secondary">
                {t("downloadReviewPacket")}
              </Button>
            ) : null}
            <Link className={buttonClassName({ variant: "secondary", size: "sm" })} to={workflowBackLink}>
              {t("stageDetailBackToWorkflow")}
            </Link>
          </div>
        </div>
        {loadError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{loadError}</p> : null}
        {loading ? <p className="mt-4 text-sm text-slate-500">{t("stageDetailLoading")}</p> : null}
        {stageRunGate && !stageRunGate.canRun ? (
          <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {getLocalizedStageRunGateReason(stageRunGate, t)}
          </p>
        ) : null}
        {stage ? (
          <div className="mt-4 grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
            <p>
              {t("stageDetailAgentId")}: {stage.agent_id}
            </p>
            <p>
              {t("updated")}: {formatDateTime(stage.updated_at)}
            </p>
          </div>
        ) : null}
      </Card>

      {stage ? (
        <>
          <StageClaimSafetyCard stage={stage} />

          <StageReviewGateCard onStageChange={handleStageChange} stage={stage} />

          <StageProviderReadinessCard readinessData={providerReadinessData} stage={stage} />

          <StageOutputPanel
            onStageChange={handleStageChange}
            stage={stage}
            stageRunGate={stageRunGate ?? undefined}
            workflowStages={workflowStages}
          />

          <StageNextActionCard
            onStageChange={handleStageChange}
            providerReadinessData={providerReadinessData}
            stage={stage}
            stages={workflowStages}
          />

          {runError ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{runError}</p> : null}
          {successMessage ? <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{successMessage}</p> : null}

          <StageEditor onStageChange={handleStageChange} stage={stage} />
        </>
      ) : null}
    </div>
  );
}
