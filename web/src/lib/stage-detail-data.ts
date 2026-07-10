import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "../api/client";
import { getProviders } from "../api/providers";
import { getQuest, getQuestStages } from "../api/quests";
import type {
  Provider,
  Quest,
  StageCard,
  User,
  WorkflowNextAction,
} from "../api/types";
import { getWorkflowNextActions } from "../api/workflow";

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
  const [providers, setProviders] = useState<readonly Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const applyStageChange = useCallback((nextStage: StageCard) => {
    setStage(nextStage);
    setStages((currentStages) =>
      currentStages.map((candidate) =>
        candidate.id === nextStage.id ? nextStage : candidate,
      ),
    );
  }, []);

  const refresh = useCallback(async () => {
    if (!questId || !stageId) {
      return;
    }

    const [nextStages, nextActions] = await Promise.all([
      getQuestStages(questId),
      getWorkflowNextActions(questId),
    ]);
    setStage(selectedStage(nextStages, stageId));
    setStages(nextStages);
    setNextAction(nextActions.actions[0] ?? null);
  }, [questId, stageId]);

  useEffect(() => {
    if (!stageId || !questId || !currentUser) {
      setQuest(null);
      setStage(null);
      setStages([]);
      setNextAction(null);
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
    ])
      .then(([nextQuest, nextStages, nextActions, visibleProviders]) => {
        if (!active) {
          return;
        }

        setQuest(nextQuest);
        setStage(selectedStage(nextStages, stageId));
        setStages(nextStages);
        setNextAction(nextActions.actions[0] ?? null);
        setProviders(visibleProviders);
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
