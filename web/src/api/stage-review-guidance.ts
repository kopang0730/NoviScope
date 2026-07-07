import { apiRequest } from "./client";
import type { StageConfidence, StageStatus } from "./types";

export type StageReviewApprovalState =
  | "pending_stage_completion"
  | "ready_for_review"
  | "approved"
  | "rejected";

export type StageReviewGuidance = {
  readonly agent_id: string;
  readonly approval_state: StageReviewApprovalState;
  readonly blocking_reason: string;
  readonly can_approve: boolean;
  readonly checklist: readonly string[];
  readonly confidence: StageConfidence;
  readonly evidence_summary: readonly string[];
  readonly review_notes: string;
  readonly review_required: boolean;
  readonly stage_id: string;
  readonly status: StageStatus;
  readonly warnings: readonly string[];
};

export function getStageReviewGuidance(stageId: string) {
  return apiRequest<StageReviewGuidance>(`/api/stages/${stageId}/review-guidance`);
}
