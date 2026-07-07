import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { getQuest, getQuestStages, getQuests, runStage } from "../api/quests";
import type { Quest, StageCard } from "../api/types";
import { useAuth } from "../auth/auth-context";
import { CanvasMainPanel } from "../components/canvas-main-panel";
import { CanvasQuestSidebar } from "../components/canvas-quest-sidebar";
import { useProviderReadinessData } from "../lib/provider-readiness-data";

export function CanvasWorkspacePage() {
  const { authReady, currentUser } = useAuth();
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
  const providerReadinessData = useProviderReadinessData();

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
      setStageRunError(error instanceof Error ? getErrorMessage(error) : "Unexpected error");
    } finally {
      setRunningStageId(null);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
      <CanvasQuestSidebar
        authReady={authReady}
        currentUser={currentUser}
        filteredQuests={filteredQuests}
        loading={questsLoading}
        loadingError={questsError}
        onQueryChange={setQuery}
        onSelectQuest={(questId) => setSearchParams({ quest: questId })}
        query={query}
        questCount={quests.length}
        selectedQuestId={selectedQuestId}
      />
      <CanvasMainPanel
        detailError={detailError}
        detailLoading={detailLoading}
        onRunStage={(stageId) => void handleRunStage(stageId)}
        providerReadinessData={providerReadinessData}
        runningStageId={runningStageId}
        selectedQuest={selectedQuest}
        selectedQuestId={selectedQuestId}
        stageRunError={stageRunError}
        stages={stages}
      />
    </div>
  );
}
