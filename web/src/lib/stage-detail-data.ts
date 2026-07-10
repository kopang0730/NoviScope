import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "../api/client";
import { getProviders } from "../api/providers";
import { getQuest, getQuestStages } from "../api/quests";
import type {
  Provider,
  Quest,
  StageCard,
  User,
  WorkflowAgentCapability,
  WorkflowNextAction,
} from "../api/types";
import { getWorkflowCapabilities, getWorkflowNextActions } from "../api/workflow";
import { useAsyncSelectionGuard } from "./use-async-selection-guard";

type StageDetailDataOptions = {
  readonly currentUser: User | null;
  readonly questId: string | null;
  readonly stageId: string | undefined;
};

function selectedStage(stages: readonly StageCard[], stageId: string) {
  const stage = stages.find((candidate) => candidate.id === stageId);
  if (!stage) {
    throw new TypeError("Stage not found in the selected quest.");
  }
  return stage;
}

export function useStageDetailData({
  currentUser,
  questId,
  stageId,
}: StageDetailDataOptions) {
  const [quest, setQuest] = useState<Quest | null>(null);
  const [stage, setStage] = useState<StageCard | null>(null);
  const [stages, setStages] = useState<readonly StageCard[]>([]);
  const [nextAction, setNextAction] = useState<WorkflowNextAction | null>(null);
  const [capabilities, setCapabilities] = useState<readonly WorkflowAgentCapability[]>([]);
  const [providers, setProviders] = useState<readonly Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const selectionKey = currentUser && questId && stageId
    ? `${currentUser.id}:${questId}:${stageId}`
    : null;
  const isCurrentSelection = useAsyncSelectionGuard(selectionKey);

  const applyStageChange = useCallback((nextStage: StageCard) => {
    if (
      !isCurrentSelection() ||
      nextStage.id !== stageId ||
      nextStage.quest_id !== questId
    ) {
      return false;
    }
    setStage(nextStage);
    setStages((currentStages) =>
      currentStages.map((candidate) =>
        candidate.id === nextStage.id ? nextStage : candidate,
      ),
    );
    return true;
  }, [isCurrentSelection, questId, stageId]);

  const refresh = useCallback(async () => {
    if (!questId || !stageId) {
      return false;
    }

    const [nextStages, nextActions] = await Promise.all([
      getQuestStages(questId),
      getWorkflowNextActions(questId),
    ]);
    if (!isCurrentSelection()) {
      return false;
    }
    setStage(selectedStage(nextStages, stageId));
    setStages(nextStages);
    setNextAction(nextActions.actions[0] ?? null);
    return true;
  }, [isCurrentSelection, questId, stageId]);

  useEffect(() => {
    if (!stageId || !questId || !currentUser) {
      setQuest(null);
      setStage(null);
      setStages([]);
      setNextAction(null);
      setCapabilities([]);
      setProviders([]);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setLoadError(null);

    void Promise.all([
      getQuest(questId),
      getQuestStages(questId),
      getWorkflowNextActions(questId),
      getProviders(),
      getWorkflowCapabilities(),
    ])
      .then(([nextQuest, nextStages, nextActions, visibleProviders, workflowCapabilities]) => {
        if (!active) {
          return;
        }

        setQuest(nextQuest);
        setStage(selectedStage(nextStages, stageId));
        setStages(nextStages);
        setNextAction(nextActions.actions[0] ?? null);
        setProviders(visibleProviders);
        setCapabilities(workflowCapabilities);
      })
      .catch((error: unknown) => {
        if (active) {
          setLoadError(getErrorMessage(error));
        }
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

  return {
    applyStageChange,
    capabilities,
    isCurrentSelection,
    loadError,
    loading,
    nextAction,
    providers,
    quest,
    refresh,
    stage,
    stages,
  };
}
