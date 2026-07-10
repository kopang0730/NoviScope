import { useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { runStage } from "../api/quests";
import type { StageCard, StageStatus } from "../api/types";
import { useAuth } from "../auth/auth-context";
import { Badge } from "../components/badge";
import { Button, buttonClassName } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { StageEditor } from "../components/stage-editor";
import { StageNextActionCard } from "../components/stage-next-action-card";
import { StageWorkbenchTabs } from "../components/stage-workbench-tabs";
import { useI18n } from "../i18n/i18n-context";
import { downloadTextFile } from "../lib/download-file";
import { formatDateTime, labelFromEnum } from "../lib/format";
import { useProviderReadinessData } from "../lib/provider-readiness-data";
import { useStageDetailData } from "../lib/stage-detail-data";
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
  const navigate = useNavigate();
  const { authReady, currentUser } = useAuth();
  const { t } = useI18n();
  const questId = searchParams.get("quest");

  const [runError, setRunError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [runningStageId, setRunningStageId] = useState<string | null>(null);
  const providerReadinessData = useProviderReadinessData();
  const {
    applyStageChange,
    loadError,
    loading,
    nextAction,
    providers,
    quest,
    refresh,
    stage,
    stages,
  } = useStageDetailData({ currentUser, questId, stageId });

  const workflowBackLink = useMemo(() => (questId ? `/?quest=${questId}` : "/"), [questId]);

  function handleWorkflowMutation(nextStage: StageCard) {
    applyStageChange(nextStage);
    setRunError(null);
    void refresh().catch((error: unknown) => {
      setRunError(getErrorMessage(error));
    });
  }

  async function handleRunStage(targetStageId: string, providerId?: string) {
    if (!questId) {
      return;
    }

    setRunningStageId(targetStageId);
    setRunError(null);
    setSuccessMessage(null);

    try {
      const updatedStage = await runStage(
        targetStageId,
        providerId ? { provider_id: providerId } : {},
      );
      await refresh();
      setSuccessMessage(
        updatedStage.status === "blocked" ? t("stageRunBlocked") : t("stageRunComplete"),
      );
      if (targetStageId !== stageId) {
        navigate(`/stages/${targetStageId}?quest=${questId}`);
      }
    } catch (error) {
      if (error instanceof Error) {
        setRunError(getErrorMessage(error));
      } else {
        throw error;
      }
    } finally {
      setRunningStageId(null);
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
          <div className="min-w-0">
            <p className="text-sm text-slate-500">{t("stageDetailTitle")}</p>
            <h1 className="mt-1 text-xl font-semibold text-slate-900">
              {stage?.title ?? t("stageDetailFallbackTitle")}
            </h1>
            {quest ? <p className="mt-2 text-sm text-slate-600">{quest.title}</p> : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {stage ? <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge> : null}
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
        {stage ? (
          <div className="mt-4 grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
            <p>{t("stageDetailAgentId")}: {stage.agent_id}</p>
            <p>{t("updated")}: {formatDateTime(stage.updated_at)}</p>
          </div>
        ) : null}
      </Card>

      {stage ? (
        <>
          <StageNextActionCard
            action={nextAction}
            onNavigate={(path) => void navigate(path)}
            onRun={(targetStageId, providerId) => void handleRunStage(targetStageId, providerId)}
            providers={providers}
            questId={questId}
            runningStageId={runningStageId}
          />

          <StageWorkbenchTabs
            mode="full"
            onRunStage={(targetStageId, providerId) => void handleRunStage(targetStageId, providerId)}
            onStageChange={handleWorkflowMutation}
            providerReadinessData={providerReadinessData}
            stage={stage}
            stages={stages}
          />

          {runError ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
              {runError}
            </p>
          ) : null}
          {successMessage ? (
            <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700" role="status">
              {successMessage}
            </p>
          ) : null}

          <details>
            <summary className="cursor-pointer rounded-lg border border-slate-200 bg-white px-5 py-4 text-sm font-semibold text-slate-900 shadow-panel sm:px-6">
              {t("stageDetailAdvancedEditor")}
            </summary>
            <div className="mt-4">
              <StageEditor onStageChange={handleWorkflowMutation} stage={stage} />
            </div>
          </details>
        </>
      ) : null}
    </div>
  );
}
