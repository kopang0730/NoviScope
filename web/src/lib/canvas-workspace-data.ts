import { useCallback, useEffect, useState } from "react";
import { getAgentAssignments } from "../api/agent-assignments";
import { getErrorMessage } from "../api/client";
import { getProviders } from "../api/providers";
import { getQuest, getQuestStages, getQuests, runStage } from "../api/quests";
import type {
  AgentAssignment,
  Provider,
  Quest,
  StageCard,
  User,
  WorkflowAgentCapability,
  WorkflowNextAction,
} from "../api/types";
import {
  getWorkflowCapabilities,
  getWorkflowCanvasTemplate,
  getWorkflowNextActions,
} from "../api/workflow";
import { useAsyncSelectionGuard } from "./use-async-selection-guard";

export type CanvasWorkspaceDataOptions = {
  readonly currentUser: User | null;
  readonly selectedQuestId: string | null;
};

export function useCanvasWorkspaceData({
  currentUser,
  selectedQuestId,
}: CanvasWorkspaceDataOptions) {
  const [quests, setQuests] = useState<readonly Quest[]>([]);
  const [questsLoading, setQuestsLoading] = useState(false);
  const [questsError, setQuestsError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [selectedQuest, setSelectedQuest] = useState<Quest | null>(null);
  const [stages, setStages] = useState<readonly StageCard[]>([]);
  const [nextActions, setNextActions] = useState<readonly WorkflowNextAction[]>([]);
  const [capabilities, setCapabilities] = useState<readonly WorkflowAgentCapability[]>([]);
  const [providers, setProviders] = useState<readonly Provider[]>([]);
  const [assignments, setAssignments] = useState<readonly AgentAssignment[]>([]);
  const [runningStageId, setRunningStageId] = useState<string | null>(null);
  const [stageRunError, setStageRunError] = useState<string | null>(null);
  const selectionKey = currentUser && selectedQuestId
    ? `${currentUser.id}:${selectedQuestId}`
    : null;
  const isCurrentSelection = useAsyncSelectionGuard(selectionKey);

  useEffect(() => {
    if (!currentUser) {
      setQuests([]);
      setQuestsError(null);
      setQuestsLoading(false);
      return;
    }

    let active = true;
    setQuestsLoading(true);
    setQuestsError(null);
    void getQuests()
      .then((nextQuests) => {
        if (active) {
          setQuests(nextQuests);
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        if (error instanceof Error) {
          setQuestsError(getErrorMessage(error));
          return;
        }
        throw error;
      })
      .finally(() => {
        if (active) {
          setQuestsLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [currentUser]);

  useEffect(() => {
    setRunningStageId(null);
    setStageRunError(null);
    if (!currentUser || !selectedQuestId) {
      setSelectedQuest(null);
      setStages([]);
      setNextActions([]);
      setCapabilities([]);
      setProviders([]);
      setAssignments([]);
      setDetailError(null);
      setDetailLoading(false);
      return;
    }

    let active = true;
    setDetailLoading(true);
    setDetailError(null);
    setSelectedQuest(null);
    setStages([]);
    setNextActions([]);
    setCapabilities([]);
    setProviders([]);
    setAssignments([]);
    void Promise.all([
      getQuest(selectedQuestId),
      getQuestStages(selectedQuestId),
      getWorkflowNextActions(selectedQuestId),
      getWorkflowCapabilities(),
      getWorkflowCanvasTemplate(),
      getProviders(),
      getAgentAssignments(),
    ])
      .then(([quest, questStages, actions, agentCapabilities, , visibleProviders, agentAssignments]) => {
        if (!active) {
          return;
        }
        setSelectedQuest(quest);
        setStages(questStages);
        setNextActions(actions.actions);
        setCapabilities(agentCapabilities);
        setProviders(visibleProviders);
        setAssignments(agentAssignments);
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        if (error instanceof Error) {
          setDetailError(getErrorMessage(error));
          return;
        }
        throw error;
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

  const runSelectedStage = useCallback(async (stageId: string, providerId?: string) => {
    if (!selectedQuest) {
      return;
    }

    setRunningStageId(stageId);
    setStageRunError(null);
    try {
      await runStage(stageId, providerId ? { provider_id: providerId } : {});
      if (!isCurrentSelection()) {
        return;
      }
      const [questStages, actions] = await Promise.all([
        getQuestStages(selectedQuest.id),
        getWorkflowNextActions(selectedQuest.id),
      ]);
      if (!isCurrentSelection()) {
        return;
      }
      setStages(questStages);
      setNextActions(actions.actions);
    } catch (error: unknown) {
      if (!isCurrentSelection()) {
        return;
      }
      if (error instanceof Error) {
        setStageRunError(getErrorMessage(error));
        return;
      }
      throw error;
    } finally {
      if (isCurrentSelection()) {
        setRunningStageId(null);
      }
    }
  }, [isCurrentSelection, selectedQuest]);

  return {
    assignments,
    capabilities,
    detailError,
    detailLoading,
    nextActions,
    providers,
    quests,
    questsError,
    questsLoading,
    runSelectedStage,
    runningStageId,
    selectedQuest,
    stageRunError,
    stages,
  };
}
