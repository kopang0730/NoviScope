import { apiRequest } from "./client";
import type {
  MarkdownArtifactManifestResponse,
  Quest,
  QuestCreateResponse,
  StageCard,
  StageStatus,
} from "./types";

type QuestsResponse = {
  quests: Quest[];
};

type StagesResponse = {
  stages: StageCard[];
};

export type CreateQuestPayload = {
  title: string;
  initial_direction: string;
};

export type UpdateStagePayload = {
  status?: StageStatus;
  summary?: string;
  input_payload?: Record<string, unknown>;
  output_payload?: Record<string, unknown>;
  evidence_payload?: Record<string, unknown>;
  human_approved?: boolean | null;
  review_notes?: string;
};

export type RunStagePayload = {
  provider_id?: string;
};

export type SelectStageIdeasPayload = {
  review_notes?: string;
  selected_idea_ids: readonly string[];
};

export async function getQuests() {
  const response = await apiRequest<QuestsResponse>("/api/quests");
  return response.quests;
}

export function createQuest(payload: CreateQuestPayload) {
  return apiRequest<QuestCreateResponse>("/api/quests", {
    body: payload,
    method: "POST",
  });
}

export function getQuest(questId: string) {
  return apiRequest<Quest>(`/api/quests/${questId}`);
}

export async function getQuestStages(questId: string) {
  const response = await apiRequest<StagesResponse>(`/api/quests/${questId}/stages`);
  return response.stages;
}

export function updateStage(stageId: string, payload: UpdateStagePayload) {
  return apiRequest<StageCard>(`/api/stages/${stageId}`, {
    body: payload,
    method: "PATCH",
  });
}

export function runStage(stageId: string, payload: RunStagePayload = {}) {
  return apiRequest<StageCard>(`/api/stages/${stageId}/run`, {
    body: payload,
    method: "POST",
  });
}

export function selectStageIdeas(stageId: string, payload: SelectStageIdeasPayload) {
  return apiRequest<StageCard>(`/api/stages/${stageId}/select-ideas`, {
    body: payload,
    method: "POST",
  });
}

export function getStageArtifacts(stageId: string) {
  return apiRequest<MarkdownArtifactManifestResponse>(`/api/stages/${stageId}/artifacts`);
}

export function buildStageArtifactDownloadPath(downloadUrl: string) {
  if (downloadUrl.startsWith("/api/")) {
    return downloadUrl;
  }

  if (downloadUrl.startsWith("/")) {
    return `/api${downloadUrl}`;
  }

  return `/api/${downloadUrl}`;
}
