import { describe, expect, it } from "vitest";
import type { WorkflowActionType, WorkflowNextAction } from "../api/types";
import { buildWorkflowActionView } from "./workflow-action-view";

function action(
  actionType: WorkflowActionType,
  overrides: Partial<WorkflowNextAction> = {},
): WorkflowNextAction {
  return {
    action_type: actionType,
    agent_id: "literature_scout",
    blocking_reason: "",
    can_run: actionType === "run_stage",
    detail: "API detail fallback",
    label: "API label fallback",
    priority: 1,
    stage_id: "stage-1",
    stage_status: "pending",
    stage_title: "Literature Scout",
    ...overrides,
  };
}

describe("buildWorkflowActionView", () => {
  it("maps runnable stages to an agent-owned run command", () => {
    const view = buildWorkflowActionView(action("run_stage"), "zh");

    expect(view.command).toBe("run");
    expect(view.disabled).toBe(false);
    expect(view.title).toContain("运行");
    expect(view.responsible).toContain("Literature Scout");
  });

  it("maps review stages to localized human review copy", () => {
    const view = buildWorkflowActionView(
      action("review_stage", { blocking_reason: "human_review_required" }),
      "zh",
    );

    expect(view.command).toBe("open_stage");
    expect(view.title).toContain("人工复核");
    expect(view.reason).toContain("继续工作流");
  });

  it("maps provider blockers to provider configuration", () => {
    const view = buildWorkflowActionView(
      action("configure_provider", { blocking_reason: "missing_provider" }),
      "en",
    );

    expect(view.command).toBe("open_providers");
    expect(view.reason).toContain("compatible provider");
  });

  it("maps other blockers to a researcher-owned stage command", () => {
    const view = buildWorkflowActionView(
      action("resolve_blocker", { blocking_reason: "missing_experiment_inputs" }),
      "en",
    );

    expect(view.command).toBe("open_stage");
    expect(view.responsible).toContain("Researcher");
    expect(view.reason).toContain("experiment inputs");
  });

  it("disables the primary command while a stage is running", () => {
    const view = buildWorkflowActionView(
      action("wait_for_stage", {
        blocking_reason: "stage_already_running",
        stage_status: "running",
      }),
      "zh",
    );

    expect(view.command).toBe("wait");
    expect(view.disabled).toBe(true);
    expect(view.reason).toContain("运行完成");
  });

  it("uses API evidence as the fallback for unknown blocking reasons", () => {
    const view = buildWorkflowActionView(
      action("resolve_blocker", { blocking_reason: "future_backend_reason" }),
      "zh",
    );

    expect(view.reason).toBe("API detail fallback");
  });
});
