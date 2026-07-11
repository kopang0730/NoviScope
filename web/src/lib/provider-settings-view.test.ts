import { describe, expect, it } from "vitest";
import type { AgentAssignment, Provider, WorkflowAgentCapability } from "../api/types";
import {
  buildAssignmentRows,
  buildAssignmentUpdates,
  filterProviders,
  isAssignmentRowDirty,
} from "./provider-settings-view";

const providers = [
  {
    base_url: "https://shared.example.com/v1",
    api_mode: "auto",
    created_at: "2026-07-10T00:00:00Z",
    default_model: "shared-model",
    id: "shared-provider",
    is_active: true,
    kind: "openai_compatible",
    name: "Shared Provider",
    owner_user_id: null,
    scope: "shared",
    updated_at: "2026-07-10T00:00:00Z",
  },
  {
    base_url: "https://personal.example.com/v1",
    api_mode: "auto",
    created_at: "2026-07-10T00:00:00Z",
    default_model: "personal-model",
    id: "personal-provider",
    is_active: true,
    kind: "custom",
    name: "Personal Provider",
    owner_user_id: "user-1",
    scope: "personal",
    updated_at: "2026-07-10T00:00:00Z",
  },
] satisfies readonly Provider[];

const assignments = [
  {
    agent_id: "demand_validator",
    display_name: "Demand Validator",
    effective_model: "shared-model",
    model_name: null,
    provider_id: "shared-provider",
    provider_is_active: true,
    provider_kind: "openai_compatible",
    provider_name: "Shared Provider",
  },
  {
    agent_id: "literature_scout",
    display_name: "Literature Scout",
    effective_model: null,
    model_name: null,
    provider_id: null,
    provider_is_active: null,
    provider_kind: null,
    provider_name: null,
  },
  {
    agent_id: "code_runner",
    display_name: "Code Runner",
    effective_model: null,
    model_name: null,
    provider_id: null,
    provider_is_active: null,
    provider_kind: null,
    provider_name: null,
  },
] satisfies readonly AgentAssignment[];

const capabilities = [
  {
    agent_id: "demand_validator",
    automation_status: "implemented",
    display_name: "Demand Validator",
    provider_requirement: "model_provider",
    stage_runner_available: true,
    status_detail: "Runnable with a model provider.",
    tool_permissions: ["web_search"],
  },
  {
    agent_id: "literature_scout",
    automation_status: "implemented",
    display_name: "Literature Scout",
    provider_requirement: "server_managed",
    stage_runner_available: true,
    status_detail: "Uses server-managed research connectors.",
    tool_permissions: ["literature_search"],
  },
  {
    agent_id: "code_runner",
    automation_status: "planned",
    display_name: "Code Runner",
    provider_requirement: "not_implemented",
    stage_runner_available: false,
    status_detail: "Planned only.",
    tool_permissions: [],
  },
] satisfies readonly WorkflowAgentCapability[];

describe("provider settings view", () => {
  it("filters visible credentials by the selected scope", () => {
    expect(filterProviders(providers, "personal").every((provider) => provider.scope === "personal")).toBe(true);
    expect(filterProviders(providers, "shared").map((provider) => provider.id)).toEqual([
      "shared-provider",
    ]);
  });

  it("builds capability-aware rows with planned and server-managed roles disabled", () => {
    const rows = buildAssignmentRows(assignments, capabilities);

    expect(rows.find((row) => row.agentId === "code_runner")?.editable).toBe(false);
    expect(rows.find((row) => row.agentId === "code_runner")?.providerRequirement).toBe(
      "not_implemented",
    );
    expect(rows.find((row) => row.agentId === "literature_scout")?.editable).toBe(false);
    expect(rows.find((row) => row.agentId === "demand_validator")?.status).toBe("implemented");
  });

  it("detects dirty rows from normalized provider and model values", () => {
    const demandRow = buildAssignmentRows(assignments, capabilities).find(
      (row) => row.agentId === "demand_validator",
    );

    expect(demandRow).toBeDefined();
    if (!demandRow) {
      return;
    }

    expect(
      isAssignmentRowDirty(demandRow, {
        modelName: "",
        providerId: "shared-provider",
      }),
    ).toBe(false);
    expect(
      isAssignmentRowDirty(demandRow, {
        modelName: "shared-model-mini",
        providerId: "shared-provider",
      }),
    ).toBe(true);
  });

  it("creates updates only for changed implemented model-provider rows", () => {
    const rows = buildAssignmentRows(assignments, capabilities);

    expect(
      buildAssignmentUpdates(rows, {
        code_runner: { modelName: "planned-model", providerId: "shared-provider" },
        demand_validator: { modelName: "shared-model-mini", providerId: "shared-provider" },
        literature_scout: { modelName: "connector-model", providerId: "shared-provider" },
      }),
    ).toEqual([
      {
        agentId: "demand_validator",
        payload: {
          model_name: "shared-model-mini",
          provider_id: "shared-provider",
        },
      },
    ]);
  });
});
