export type UserRole = "admin" | "member";
export type ProviderKind = "openai_compatible" | "anthropic" | "custom";
export type ProviderScope = "personal" | "shared";
export type InviteStatus = "active" | "disabled" | "exhausted";
export type StageConfidence = "high" | "medium" | "low" | "unknown";
export type QuestStatus =
  | "draft"
  | "demand_review"
  | "idea_selection"
  | "lightweight_experiment"
  | "full_experiment"
  | "writing"
  | "complete"
  | "archived";
export type StageStatus = "pending" | "running" | "blocked" | "complete";

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Provider {
  id: string;
  name: string;
  kind: ProviderKind;
  scope: ProviderScope;
  owner_user_id: string | null;
  base_url: string;
  default_model: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InviteCode {
  id: string;
  code: string;
  status: InviteStatus;
  max_uses: number;
  used_count: number;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentAssignment {
  agent_id: string;
  display_name: string;
  provider_id: string | null;
  provider_name: string | null;
  provider_kind: ProviderKind | null;
  provider_is_active: boolean | null;
  model_name: string | null;
  effective_model: string | null;
}

export interface Quest {
  id: string;
  owner_user_id: string | null;
  title: string;
  initial_direction: string;
  status: QuestStatus;
  created_at: string;
  updated_at: string;
}

export interface StageCard {
  id: string;
  quest_id: string;
  agent_id: string;
  title: string;
  status: StageStatus;
  confidence: StageConfidence;
  summary: string;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  evidence_payload: Record<string, unknown>;
  human_approved: boolean | null;
  review_notes: string;
  created_at: string;
  updated_at: string;
}

export interface QuestCreateResponse {
  id: string;
  owner_user_id: string | null;
  title: string;
  initial_direction: string;
  status: QuestStatus;
  first_stage: StageCard;
}
