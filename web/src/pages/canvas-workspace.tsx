import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { getProviders } from "../api/providers";
import { getQuest, getQuestStages, getQuests, runStage } from "../api/quests";
import type {
  Provider,
  Quest,
  StageCard,
  WorkflowAgentCapability,
  WorkflowNextAction,
} from "../api/types";
import {
  getWorkflowCapabilities,
  getWorkflowCanvasTemplate,
  getWorkflowNextActions,
} from "../api/workflow";
import { useAuth } from "../auth/auth-context";
import { Badge } from "../components/badge";
import { buttonClassName } from "../components/button";
import { CanvasReviewPacketButton } from "../components/canvas-review-packet-button";
import { Card } from "../components/card";
import { Input, Select } from "../components/input";
import { QuestNextActionStrip } from "../components/quest-next-action-strip";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import { questTone, stageTone } from "../lib/status-tones";

function directionSummary(value: string) {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > 150 ? `${normalized.slice(0, 150)}...` : normalized;
}

export function CanvasWorkspacePage() {
  const { authReady, currentUser } = useAuth();
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const [quests, setQuests] = useState<Quest[]>([]);
  const [questsLoading, setQuestsLoading] = useState(false);
  const [questsError, setQuestsError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [selectedQuest, setSelectedQuest] = useState<Quest | null>(null);
  const [stages, setStages] = useState<StageCard[]>([]);
  const [nextActions, setNextActions] = useState<readonly WorkflowNextAction[]>([]);
  const [capabilities, setCapabilities] = useState<readonly WorkflowAgentCapability[]>([]);
  const [providers, setProviders] = useState<readonly Provider[]>([]);
  const [runningStageId, setRunningStageId] = useState<string | null>(null);
  const [stageRunError, setStageRunError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [railCollapsed, setRailCollapsed] = useState(false);

  const selectedQuestId = searchParams.get("quest");

  const loadQuests = useCallback(async () => {
    if (!currentUser) {
      setQuests([]);
      setSelectedQuest(null);
      setStages([]);
      setNextActions([]);
      setCapabilities([]);
      setProviders([]);
      setQuestsError(null);
      setQuestsLoading(false);
      return;
    }

    setQuestsLoading(true);
    setQuestsError(null);

    try {
      setQuests(await getQuests());
    } catch (error) {
      setQuestsError(error instanceof Error ? getErrorMessage(error) : "Unexpected error");
    } finally {
      setQuestsLoading(false);
    }
  }, [currentUser]);

  useEffect(() => {
    void loadQuests();
  }, [loadQuests]);

  const filteredQuests = useMemo(() => {
    return quests.filter((quest) => {
      const normalizedQuery = query.trim().toLowerCase();
      return (
        normalizedQuery.length === 0 ||
        quest.title.toLowerCase().includes(normalizedQuery) ||
        quest.initial_direction.toLowerCase().includes(normalizedQuery)
      );
    });
  }, [query, quests]);

  useEffect(() => {
    if (!filteredQuests.length) {
      return;
    }

    if (!selectedQuestId || !filteredQuests.some((quest) => quest.id === selectedQuestId)) {
      setSearchParams({ quest: filteredQuests[0].id }, { replace: true });
    }
  }, [filteredQuests, selectedQuestId, setSearchParams]);

  useEffect(() => {
    if (!currentUser || !selectedQuestId) {
      setSelectedQuest(null);
      setStages([]);
      setNextActions([]);
      setCapabilities([]);
      setProviders([]);
      setDetailError(null);
      setStageRunError(null);
      setDetailLoading(false);
      return;
    }

    let active = true;
    setDetailLoading(true);
    setDetailError(null);
    setStageRunError(null);
    setSelectedQuest(null);
    setStages([]);
    setNextActions([]);
    setCapabilities([]);
    setProviders([]);

    void Promise.all([
      getQuest(selectedQuestId),
      getQuestStages(selectedQuestId),
      getWorkflowNextActions(selectedQuestId),
      getWorkflowCapabilities(),
      getWorkflowCanvasTemplate(),
      getProviders(),
    ])
      .then(([quest, questStages, nextActionResponse, agentCapabilities, , visibleProviders]) => {
        if (!active) {
          return;
        }
        setSelectedQuest(quest);
        setStages(questStages);
        setNextActions(nextActionResponse.actions);
        setCapabilities(agentCapabilities);
        setProviders(visibleProviders);
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        setSelectedQuest(null);
        setStages([]);
        setNextActions([]);
        setCapabilities([]);
        setProviders([]);
        setDetailError(getErrorMessage(error));
      })
      .finally(() => {
        if (active) {
          setDetailLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [currentUser, selectedQuestId]);

  async function handleRunStage(stageId: string, providerId?: string) {
    if (!selectedQuest) {
      return;
    }

    setRunningStageId(stageId);
    setStageRunError(null);

    try {
      await runStage(stageId, providerId ? { provider_id: providerId } : {});
      const [questStages, nextActionResponse] = await Promise.all([
        getQuestStages(selectedQuest.id),
        getWorkflowNextActions(selectedQuest.id),
      ]);
      setStages(questStages);
      setNextActions(nextActionResponse.actions);
    } catch (error) {
      setStageRunError(error instanceof Error ? getErrorMessage(error) : "Unexpected error");
    } finally {
      setRunningStageId(null);
    }
  }

  return (
    <div
      className={[
        "grid min-w-0 gap-4",
        railCollapsed
          ? "lg:grid-cols-[132px_minmax(0,1fr)]"
          : "lg:grid-cols-[280px_minmax(0,1fr)]",
      ].join(" ")}
    >
      <aside className="hidden h-fit rounded-lg border border-slate-200 bg-white p-3 shadow-panel lg:sticky lg:top-4 lg:block">
        <div className="flex items-center justify-between gap-2">
          {!railCollapsed ? <h1 className="text-base font-semibold text-slate-900">{t("navCanvas")}</h1> : null}
          <button
            aria-expanded={!railCollapsed}
            className="min-h-11 rounded-lg border border-slate-300 px-3 text-xs font-medium text-slate-700 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
            onClick={() => setRailCollapsed((current) => !current)}
            type="button"
          >
            {railCollapsed ? t("questRailExpand") : t("questRailCollapse")}
          </button>
        </div>

        {!railCollapsed ? (
          <>
            <Link
              className={buttonClassName({ className: "mt-3 min-h-11 w-full", variant: "primary" })}
              to="/quests/new"
            >
              {t("navNewQuest")}
            </Link>
            <div className="mt-4">
              <Input
                label={t("questSearch")}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t("questSearchPlaceholder")}
                value={query}
              />
            </div>

            {!currentUser && authReady ? (
              <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                {t("questSignInPrompt")}
              </p>
            ) : null}
            {questsError ? (
              <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {questsError}
              </p>
            ) : null}
            {questsLoading ? <p className="mt-4 text-sm text-slate-500">{t("loadingQuests")}</p> : null}
            {!questsLoading && filteredQuests.length === 0 ? (
              <p className="mt-4 rounded-lg border border-dashed border-slate-300 px-3 py-5 text-sm text-slate-500">
                {quests.length === 0 ? t("noQuestsAvailable") : t("noQuestsMatch")}
              </p>
            ) : null}

            {filteredQuests.length > 0 ? (
              <div className="mt-4 space-y-2">
                {filteredQuests.map((quest) => {
                  const isSelected = quest.id === selectedQuestId;
                  return (
                    <button
                      className={[
                        "w-full rounded-lg border px-3 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2",
                        isSelected
                          ? "border-teal-300 bg-teal-50"
                          : "border-slate-200 bg-white hover:bg-slate-50",
                      ].join(" ")}
                      key={quest.id}
                      onClick={() => setSearchParams({ quest: quest.id })}
                      type="button"
                    >
                      <p className="break-words text-sm font-medium text-slate-900">{quest.title}</p>
                      <p className="mt-1 line-clamp-2 text-xs text-slate-600">
                        {directionSummary(quest.initial_direction)}
                      </p>
                    </button>
                  );
                })}
              </div>
            ) : null}
          </>
        ) : null}
      </aside>

      <main className="min-w-0 space-y-4">
        <div className="lg:hidden">
          <Select
            className="min-h-11"
            disabled={quests.length === 0}
            label={t("questSelector")}
            onChange={(event) => setSearchParams({ quest: event.target.value })}
            value={selectedQuestId ?? ""}
          >
            {quests.length === 0 ? <option value="">{t("noQuestsAvailable")}</option> : null}
            {quests.map((quest) => (
              <option key={quest.id} value={quest.id}>
                {quest.title}
              </option>
            ))}
          </Select>
        </div>

        <Card className="min-w-0">
          {!selectedQuestId ? <p className="text-sm text-slate-500">{t("selectQuestForStages")}</p> : null}
          {detailError ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {detailError}
            </p>
          ) : null}
          {stageRunError ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {stageRunError}
            </p>
          ) : null}
          {detailLoading ? <p className="text-sm text-slate-500">{t("loadingQuestDetail")}</p> : null}

          {selectedQuest ? (
            <div className="space-y-5">
              <header className="flex flex-col gap-3 border-b border-slate-200 pb-5 md:flex-row md:items-start md:justify-between">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("currentQuest")}</p>
                  <h1 className="mt-1 break-words text-lg font-semibold text-slate-950">{selectedQuest.title}</h1>
                  <p className="mt-2 max-w-4xl break-words text-sm leading-6 text-slate-600">
                    {selectedQuest.initial_direction}
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <Badge tone={questTone(selectedQuest.status)}>{labelFromEnum(selectedQuest.status)}</Badge>
                    <Badge tone="gray">
                      {t("updated")} {formatDateTime(selectedQuest.updated_at)}
                    </Badge>
                  </div>
                </div>
                <CanvasReviewPacketButton quest={selectedQuest} stages={stages} />
              </header>

              <QuestNextActionStrip
                actions={nextActions}
                capabilities={capabilities}
                onRun={(stageId, providerId) => void handleRunStage(stageId, providerId)}
                providers={providers}
                questId={selectedQuest.id}
                runningStageId={runningStageId}
              />

              <section aria-labelledby="workflow-stage-records-title">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-base font-semibold text-slate-900" id="workflow-stage-records-title">
                    {t("workflowTitle")}
                  </h2>
                  <Badge tone="gray">{stages.length}</Badge>
                </div>
                {stages.length === 0 ? (
                  <p className="mt-3 border-t border-dashed border-slate-300 py-5 text-sm text-slate-500">
                    {t("noStagesFound")}
                  </p>
                ) : (
                  <ul className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
                    {stages.map((stage) => (
                      <li
                        className="flex min-w-0 flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between"
                        key={stage.id}
                      >
                        <div className="min-w-0">
                          <p className="break-words text-sm font-medium text-slate-900">{stage.title}</p>
                          <p className="mt-1 break-all text-xs text-slate-500">{stage.agent_id}</p>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge>
                          <Link
                            className={buttonClassName({ className: "min-h-11", variant: "secondary" })}
                            to={`/stages/${stage.id}?quest=${selectedQuest.id}`}
                          >
                            {t("open")}
                          </Link>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          ) : null}
        </Card>
      </main>
    </div>
  );
}
