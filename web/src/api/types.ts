export type UserRole = "admin" | "member";
export type ProviderKind = "openai_compatible" | "anthropic" | "custom";
export type ProviderApiMode = "auto" | "chat_completions" | "responses";
export type ProviderScope = "personal" | "shared";
export type InviteStatus = "active" | "disabled" | "exhausted";
export type StageConfidence = "high" | "medium" | "low" | "unknown";
export type MarkdownArtifactKey =
  | "chinese_research_brief_markdown"
  | "english_research_brief_markdown"
  | "meeting_outline_markdown"
  | "ieee_paper_skeleton_markdown";
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

export interface PublicVersionInfo {
  app_version: string;
}

export interface AdminVersionInfo {
  app_version: string;
  local_branch: string | null;
  local_commit: string | null;
  local_commit_short: string | null;
  local_dirty: boolean | null;
  github_repo: string;
  github_branch: string;
  remote_commit: string | null;
  remote_commit_short: string | null;
  update_available: boolean;
  check_error: string | null;
  checked_at: string;
}

export interface Provider {
  id: string;
  name: string;
  kind: ProviderKind;
  scope: ProviderScope;
  owner_user_id: string | null;
  base_url: string;
  api_mode: ProviderApiMode;
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

export interface MarkdownArtifactManifestItem {
  readonly key: MarkdownArtifactKey;
  readonly title: string;
  readonly filename: string;
  readonly media_type: string;
  readonly available: boolean;
  readonly download_url: string;
  readonly missing_reason: string;
}

export interface MarkdownArtifactManifestResponse {
  readonly stage_id: string;
  readonly artifacts: readonly MarkdownArtifactManifestItem[];
}

export type WorkflowActionType =
  | "configure_provider"
  | "resolve_blocker"
  | "review_stage"
  | "run_stage"
  | "wait_for_stage";

export type AutomationStatus = "implemented" | "planned";
export type ProviderRequirement = "model_provider" | "not_implemented" | "server_managed";

export interface WorkflowAgentCapability {
  readonly agent_id: string;
  readonly automation_status: AutomationStatus;
  readonly display_name: string;
  readonly provider_requirement: ProviderRequirement;
  readonly stage_runner_available: boolean;
  readonly status_detail: string;
  readonly tool_permissions: readonly string[];
}

export interface WorkflowCapabilitiesResponse {
  readonly agents: readonly WorkflowAgentCapability[];
  readonly implemented_count: number;
  readonly planned_count: number;
  readonly total_count: number;
}

export type CanvasRole = "audit_gate" | "core_stage" | "planned_extension";
export type CanvasEdgeKind =
  | "audit_feedback"
  | "default_flow"
  | "human_gate"
  | "planned_extension";

export interface WorkflowCanvasNode {
  readonly agent_id: string;
  readonly canvas_role: CanvasRole;
  readonly column: number;
  readonly display_name: string;
  readonly lane_id: string;
  readonly row: number;
}

export interface WorkflowCanvasEdge {
  readonly edge_kind: CanvasEdgeKind;
  readonly from_agent_id: string;
  readonly label: string;
  readonly to_agent_id: string;
}

export interface WorkflowCanvasLane {
  readonly description: string;
  readonly lane_id: string;
  readonly title: string;
}

export interface WorkflowCanvasTemplate {
  readonly core_flow_agent_ids: readonly string[];
  readonly edges: readonly WorkflowCanvasEdge[];
  readonly entry_agent_id: string;
  readonly lanes: readonly WorkflowCanvasLane[];
  readonly nodes: readonly WorkflowCanvasNode[];
  readonly terminal_agent_id: string;
}

export interface WorkflowNextAction {
  readonly action_type: WorkflowActionType;
  readonly agent_id: string;
  readonly blocking_reason: string;
  readonly can_run: boolean;
  readonly detail: string;
  readonly label: string;
  readonly priority: number;
  readonly stage_id: string;
  readonly stage_status: StageStatus;
  readonly stage_title: string;
}

export interface WorkflowNextActionsResponse {
  readonly quest_id: string;
  readonly action_count: number;
  readonly actions: readonly WorkflowNextAction[];
}
