import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { getQuest, getQuestStages, getQuests, runStage } from "../api/quests";
import type { Quest, StageCard } from "../api/types";
import { useAuth } from "../auth/auth-context";
import { Badge } from "../components/badge";
import { buttonClassName } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input } from "../components/input";
import { ResearchCanvas } from "../components/research-canvas";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import { questTone } from "../lib/status-tones";

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
  const [runningStageId, setRunningStageId] = useState<string | null>(null);
  const [stageRunError, setStageRunError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const selectedQuestId = searchParams.get("quest");

  const loadQuests = useCallback(async () => {
    if (!currentUser) {
      setQuests([]);
      setSelectedQuest(null);
      setStages([]);
      setQuestsError(null);
      setQuestsLoading(false);
      return;
    }

    setQuestsLoading(true);
    setQuestsError(null);

    try {
      setQuests(await getQuests());
    } catch (error) {
      setQuestsError(getErrorMessage(error));
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
      setDetailError(null);
      setStageRunError(null);
      setDetailLoading(false);
      return;
    }

    let active = true;
    setDetailLoading(true);
    setDetailError(null);
    setStageRunError(null);

    void Promise.all([getQuest(selectedQuestId), getQuestStages(selectedQuestId)])
      .then(([quest, questStages]) => {
        if (!active) {
          return;
        }
        setSelectedQuest(quest);
        setStages(questStages);
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        setSelectedQuest(null);
        setStages([]);
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

  async function handleRunStage(stageId: string) {
    setRunningStageId(stageId);
    setStageRunError(null);

    try {
      const updatedStage = await runStage(stageId);
      setStages((currentStages) =>
        currentStages.map((stage) => (stage.id === updatedStage.id ? updatedStage : stage)),
      );
    } catch (error) {
      setStageRunError(getErrorMessage(error));
    } finally {
      setRunningStageId(null);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
      <Card className="h-fit xl:sticky xl:top-4">
        <CardHeading
          action={
            <Link className={buttonClassName({ size: "sm", variant: "primary" })} to="/quests/new">
              {t("navNewQuest")}
            </Link>
          }
          description={t("canvasWorkspaceDescription")}
          title={t("navCanvas")}
        />

        <div className="mt-5">
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
        {questsError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{questsError}</p> : null}
        {questsLoading ? <p className="mt-4 text-sm text-slate-500">{t("loadingQuests")}</p> : null}
        {!questsLoading && filteredQuests.length === 0 ? (
          <p className="mt-4 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
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
                    "w-full rounded-lg border px-4 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2",
                    isSelected ? "border-teal-300 bg-teal-50 shadow-sm" : "border-slate-200 bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={quest.id}
                  onClick={() => setSearchParams({ quest: quest.id })}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-medium text-slate-900">{quest.title}</p>
                    <Badge tone={questTone(quest.status)}>{labelFromEnum(quest.status)}</Badge>
                  </div>
                  <p className="mt-2 line-clamp-3 text-xs text-slate-600">{directionSummary(quest.initial_direction)}</p>
                  <p className="mt-2 text-xs text-slate-500">
                    {t("updated")} {formatDateTime(quest.updated_at)}
                  </p>
                </button>
              );
            })}
          </div>
        ) : null}
      </Card>

      <div className="min-w-0 space-y-4">
        <Card className="overflow-hidden">
          <CardHeading description={t("canvasWorkspaceMainDescription")} title={t("researchCanvasTitle")} />
          {!selectedQuestId ? <p className="mt-4 text-sm text-slate-500">{t("selectQuestForStages")}</p> : null}
          {detailError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{detailError}</p> : null}
          {stageRunError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{stageRunError}</p> : null}
          {detailLoading ? <p className="mt-4 text-sm text-slate-500">{t("loadingQuestDetail")}</p> : null}

          {selectedQuest ? (
            <div className="mt-5 space-y-4">
              <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("currentQuest")}</p>
                  <h2 className="mt-1 text-xl font-semibold text-slate-950">{selectedQuest.title}</h2>
                  <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">{selectedQuest.initial_direction}</p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <Badge tone={questTone(selectedQuest.status)}>{labelFromEnum(selectedQuest.status)}</Badge>
                  <Badge tone="gray">
                    {t("updated")} {formatDateTime(selectedQuest.updated_at)}
                  </Badge>
                </div>
              </div>

              {stages.length === 0 ? (
                <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
                  {t("noStagesFound")}
                </p>
              ) : (
                <ResearchCanvas
                  onRunStage={(stageId) => void handleRunStage(stageId)}
                  runningStageId={runningStageId}
                  selectedQuest={selectedQuest}
                  showHeading={false}
                  stages={stages}
                />
              )}
            </div>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
