import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/auth-context";
import { Badge } from "../components/badge";
import { CanvasReviewPacketButton } from "../components/canvas-review-packet-button";
import {
  CanvasQuestRail,
  CanvasQuestSelector,
} from "../components/canvas-quest-navigation";
import { Card } from "../components/card";
import { QuestNextActionStrip } from "../components/quest-next-action-strip";
import { ResearchCanvas } from "../components/research-canvas";
import { useI18n } from "../i18n/i18n-context";
import { useCanvasWorkspaceData } from "../lib/canvas-workspace-data";
import { formatDateTime, labelFromEnum } from "../lib/format";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import { questTone } from "../lib/status-tones";

export function CanvasWorkspacePage() {
  const { authReady, currentUser } = useAuth();
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedQuestId = searchParams.get("quest");
  const data = useCanvasWorkspaceData({ currentUser, selectedQuestId });
  const selectQuest = useCallback(
    (questId: string) => setSearchParams({ quest: questId }),
    [setSearchParams],
  );
  const replaceQuest = useCallback(
    (questId: string) => setSearchParams({ quest: questId }, { replace: true }),
    [setSearchParams],
  );

  const providerReadinessData: ProviderReadinessData = useMemo(
    () => ({
      assignments: data.assignments,
      error: null,
      loaded: !data.detailLoading,
      loading: data.detailLoading,
      providers: data.providers,
    }),
    [data.assignments, data.detailLoading, data.providers],
  );

  return (
    <div className="grid min-w-0 gap-4 lg:grid-cols-[auto_minmax(0,1fr)]">
      <CanvasQuestRail
        authReady={authReady}
        currentUser={currentUser}
        error={data.questsError}
        loading={data.questsLoading}
        onReplaceQuest={replaceQuest}
        onSelectQuest={selectQuest}
        quests={data.quests}
        selectedQuestId={selectedQuestId}
      />

      <main className="min-w-0 space-y-4">
        <CanvasQuestSelector
          onSelectQuest={selectQuest}
          quests={data.quests}
          selectedQuestId={selectedQuestId}
        />

        <Card className="min-w-0">
          {!selectedQuestId ? <p className="text-sm text-slate-500">{t("selectQuestForStages")}</p> : null}
          {data.detailError ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {data.detailError}
            </p>
          ) : null}
          {data.stageRunError ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {data.stageRunError}
            </p>
          ) : null}
          {data.detailLoading ? <p className="text-sm text-slate-500">{t("loadingQuestDetail")}</p> : null}

          {data.selectedQuest ? (
            <div className="space-y-5">
              <header className="flex flex-col gap-3 border-b border-slate-200 pb-5 md:flex-row md:items-start md:justify-between">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("currentQuest")}</p>
                  <h1 className="mt-1 break-words text-lg font-semibold text-slate-950">{data.selectedQuest.title}</h1>
                  <p className="mt-2 max-w-4xl break-words text-sm leading-6 text-slate-600">
                    {data.selectedQuest.initial_direction}
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <Badge tone={questTone(data.selectedQuest.status)}>{labelFromEnum(data.selectedQuest.status)}</Badge>
                    <Badge tone="gray">
                      {t("updated")} {formatDateTime(data.selectedQuest.updated_at)}
                    </Badge>
                  </div>
                </div>
                <CanvasReviewPacketButton quest={data.selectedQuest} stages={data.stages} />
              </header>

              <QuestNextActionStrip
                actions={data.nextActions}
                capabilities={data.capabilities}
                currentUserId={currentUser?.id ?? null}
                onRun={(stageId, providerId) => void data.runSelectedStage(stageId, providerId)}
                providers={data.providers}
                questId={data.selectedQuest.id}
                runningStageId={data.runningStageId}
              />

              <ResearchCanvas
                capabilities={data.capabilities}
                currentUserId={currentUser?.id ?? null}
                nextAction={data.nextActions[0] ?? null}
                onRunStage={(stageId, providerId) => void data.runSelectedStage(stageId, providerId)}
                providerReadinessData={providerReadinessData}
                runningStageId={data.runningStageId}
                stages={data.stages}
              />
            </div>
          ) : null}
        </Card>
      </main>
    </div>
  );
}
