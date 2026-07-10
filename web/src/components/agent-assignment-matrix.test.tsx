import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type {
  AgentAssignment,
  Provider,
  User,
  WorkflowAgentCapability,
} from "../api/types";
import { I18nProvider } from "../i18n/i18n-context";
import { AgentAssignmentMatrix } from "./agent-assignment-matrix";

const capabilityDefinitions = [
  ["demand_validator", "Demand Validator", "implemented", "model_provider"],
  ["research_refiner", "Research Refiner", "planned", "not_implemented"],
  ["literature_scout", "Literature Scout", "implemented", "server_managed"],
  ["gap_analyst", "Gap Analyst", "planned", "not_implemented"],
  ["idea_generator", "Idea Generator", "implemented", "model_provider"],
  ["experiment_planner", "Experiment Planner", "implemented", "model_provider"],
  ["code_runner", "Code Runner", "planned", "not_implemented"],
  ["evidence_auditor", "Evidence Auditor", "planned", "not_implemented"],
  ["paper_meeting_writer", "Paper and Meeting Writer", "implemented", "model_provider"],
] as const;

const capabilities = capabilityDefinitions.map(
  ([agentId, displayName, status, requirement]): WorkflowAgentCapability => ({
    agent_id: agentId,
    automation_status: status,
    display_name: displayName,
    provider_requirement: requirement,
    stage_runner_available: status === "implemented",
    status_detail:
      status === "planned"
        ? "Planned only; no automated stage runner exists yet."
        : requirement === "server_managed"
          ? "Runnable through server-managed research connectors."
          : "Runnable when a compatible model provider is configured.",
    tool_permissions: [],
  }),
);

const assignments = capabilityDefinitions.map(
  ([agentId, displayName]): AgentAssignment => ({
    agent_id: agentId,
    display_name: displayName,
    effective_model: agentId === "demand_validator" ? "shared-model" : null,
    model_name: null,
    provider_id: agentId === "demand_validator" ? "shared-provider" : null,
    provider_is_active: agentId === "demand_validator" ? true : null,
    provider_kind: agentId === "demand_validator" ? "openai_compatible" : null,
    provider_name: agentId === "demand_validator" ? "Shared Lab Model" : null,
  }),
);

const providers = [
  {
    base_url: "https://shared.example.com/v1",
    created_at: "2026-07-10T00:00:00Z",
    default_model: "shared-model",
    id: "shared-provider",
    is_active: true,
    kind: "openai_compatible",
    name: "Shared Lab Model",
    owner_user_id: null,
    scope: "shared",
    updated_at: "2026-07-10T00:00:00Z",
  },
] satisfies readonly Provider[];

const admin = {
  created_at: "2026-07-10T00:00:00Z",
  display_name: "Admin",
  email: "admin@example.com",
  id: "admin-1",
  is_active: true,
  role: "admin",
  updated_at: "2026-07-10T00:00:00Z",
} satisfies User;

const member = {
  ...admin,
  display_name: "Member",
  email: "member@example.com",
  id: "member-1",
  role: "member",
} satisfies User;

type MatrixOverrides = {
  readonly currentUser?: User;
  readonly onReload?: () => Promise<void>;
  readonly onUpdate?: (
    agentId: string,
    payload: { readonly model_name?: string | null; readonly provider_id: string | null },
  ) => Promise<AgentAssignment>;
};

function renderMatrix(overrides: MatrixOverrides = {}) {
  return render(
    <I18nProvider>
      <AgentAssignmentMatrix
        assignments={assignments}
        capabilities={capabilities}
        currentUser={overrides.currentUser ?? admin}
        error={null}
        loading={false}
        onReload={overrides.onReload ?? vi.fn().mockResolvedValue(undefined)}
        onUpdate={overrides.onUpdate ?? vi.fn().mockResolvedValue(assignments[0])}
        providers={providers}
      />
    </I18nProvider>,
  );
}

describe("AgentAssignmentMatrix", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    window.localStorage.setItem("noviscope-language", "en");
  });

  it("renders nine capability rows and disables all four planned roles", () => {
    renderMatrix();

    const table = screen.getByRole("table", { name: "Agent defaults" });
    expect(within(table).getAllByRole("row")).toHaveLength(10);
    expect(within(table).getAllByText("Planned")).toHaveLength(4);

    for (const roleName of ["Research Refiner", "Gap Analyst", "Code Runner", "Evidence Auditor"]) {
      const row = within(table).getByRole("row", { name: new RegExp(roleName) });
      expect(within(row).getByRole("combobox")).toBeDisabled();
      expect(within(row).getByRole("textbox")).toBeDisabled();
    }
  });

  it("shows effective shared defaults to members without a save control", () => {
    renderMatrix({ currentUser: member });

    const demandRow = screen.getByRole("row", { name: /Demand Validator/ });
    expect(within(demandRow).getByRole("combobox")).toHaveValue("shared-provider");
    expect(within(demandRow).getByText("shared-model")).toBeInTheDocument();
    expect(within(demandRow).getByRole("combobox")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Save shared defaults" })).not.toBeInTheDocument();
  });

  it("batches two dirty admin rows behind one page-level save", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn().mockImplementation(
      (agentId: string) =>
        Promise.resolve(
          assignments.find((assignment) => assignment.agent_id === agentId) ?? assignments[0],
        ),
    );
    const onReload = vi.fn().mockResolvedValue(undefined);
    renderMatrix({ onReload, onUpdate });

    await user.type(
      screen.getByRole("textbox", { name: "Demand Validator Model override" }),
      "shared-model-mini",
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Idea Generator Default provider" }),
      "shared-provider",
    );
    await user.click(screen.getByRole("button", { name: "Save shared defaults" }));

    expect(onUpdate).toHaveBeenCalledTimes(2);
    expect(onUpdate).toHaveBeenCalledWith("demand_validator", {
      model_name: "shared-model-mini",
      provider_id: "shared-provider",
    });
    expect(onUpdate).toHaveBeenCalledWith("idea_generator", {
      model_name: null,
      provider_id: "shared-provider",
    });
    expect(onReload).toHaveBeenCalledTimes(1);
  });

  it("reloads after partial failure and names only the failed role", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn().mockImplementation((agentId: string) => {
      if (agentId === "idea_generator") {
        return Promise.reject(new Error("provider rejected"));
      }
      return Promise.resolve(
        assignments.find((assignment) => assignment.agent_id === agentId) ?? assignments[0],
      );
    });
    const onReload = vi.fn().mockResolvedValue(undefined);
    renderMatrix({ onReload, onUpdate });

    await user.type(
      screen.getByRole("textbox", { name: "Demand Validator Model override" }),
      "shared-model-mini",
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Idea Generator Default provider" }),
      "shared-provider",
    );
    await user.click(screen.getByRole("button", { name: "Save shared defaults" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Idea Generator (idea_generator)");
    expect(alert).not.toHaveTextContent("Demand Validator (demand_validator)");
    expect(screen.queryByText("Shared defaults saved.")).not.toBeInTheDocument();
    expect(onReload).toHaveBeenCalledTimes(1);
  });
});
