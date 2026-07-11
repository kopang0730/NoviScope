# Compact Canvas Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize NoviScope's Web MVP into a compact research workbench with one authoritative next action, five macro phases containing nine truthful agent capabilities, progressive Quest intake, capability-aware provider configuration, and aligned stage detail views.

**Architecture:** Keep the backend workflow graph, workflow-next-actions, capability registry, provider visibility, and stage-run APIs as the sources of truth. Add a typed frontend workflow client and pure macro-phase view model, then compose shared action-strip and stage-workbench primitives across Canvas and Stage Detail. Personal provider overrides remain per-run through the existing `provider_id` request field; only administrators persist shared agent defaults.

**Tech Stack:** React 19, TypeScript 5.7 strict mode, React Router 7, Tailwind CSS 3.4, Vite 6, Vitest, Testing Library, Playwright, FastAPI, existing NoviScope REST APIs.

## Global Constraints

- Begin execution in an isolated worktree created with `superpowers:using-git-worktrees`; do not implement in the shared main worktree.
- Base the worktree on a branch that contains workflow capabilities, Canvas template, workflow graph, workflow-next-actions, and the provider-scope implementation.
- Do not merge PRs or resolve GitHub review threads without explicit user approval.
- Keep the five macro phases as the user-facing navigation model; expose all nine agent roles with truthful `implemented` or `planned` status.
- Never display a planned agent as runnable, completed, or provider-configurable.
- Render one authoritative next-action component. Other components may highlight its stage but must not calculate or present a competing action.
- Personal providers are selected for a single stage run through `provider_id`; the MVP does not persist personal agent defaults.
- Preserve the formal evidence and human-review trust gates. The frontend must not infer experiment results or formal-claim readiness.
- Chinese and English strings ship together through the existing typed translation table.
- Mobile primary touch targets are at least 44px. The default mobile Canvas uses a vertical phase path and a collapsed inspector.
- Do not add React Flow or another graph-editor dependency.
- Use Lucide icons only if an icon dependency is introduced; do not use emoji or hand-authored SVG icons.
- Run `npm run build`, frontend tests, backend contract tests, and real-browser visual QA before handoff.

---

### Task 1: Lock the Design Contract and Add the Frontend Test Harness

**Files:**
- Modify: `DESIGN.md`
- Modify: `web/package.json`
- Modify: `web/package-lock.json`
- Modify: `web/vite.config.ts`
- Create: `web/src/test/setup.ts`
- Create: `web/src/lib/research-workbench.test.ts`
- Create: `web/src/lib/research-workbench.ts`

**Interfaces:**
- Produces: `MacroPhaseId`, `MacroPhaseDefinition`, `macroPhaseDefinitions`, and `phaseForAgentId(agentId: string)`.
- Consumes: existing agent IDs from `web/src/lib/stages.ts` and planned agent IDs as literal constants.
- Later tasks rely on the exact five-phase ordering and nine-agent membership defined here.

- [ ] **Step 1: Update the design-system contract before component work**

Replace the current `Research Canvas` section in `DESIGN.md` with explicit contracts for:

```markdown
### Compact Research Workbench

- One authoritative next-action strip appears before workflow navigation.
- Desktop uses Quest rail, research surface, and contextual inspector.
- Mobile uses a Quest selector, sticky next action, vertical phase path, and collapsed inspector.
- Five macro phases contain nine agent roles; planned roles remain visible but disabled.
- The Canvas is workflow navigation, not a draggable workflow editor.
```

Add `Next Action Strip`, `Macro Phase Path`, `Stage Workbench Tabs`, and provider matrix states to the component section. Record 44px touch targets, no duplicated action summaries, no nested top-level cards, and bilingual copy parity.

- [ ] **Step 2: Add the test dependencies and scripts**

Run from `web/`:

```bash
npm install --save-dev vitest jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom @playwright/test @axe-core/playwright
```

Add these scripts to `web/package.json`:

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test"
  }
}
```

Add `/// <reference types="vitest/config" />` at the top of `web/vite.config.ts`
and preserve the existing API proxy while adding the test block:

```ts
/// <reference types="vitest/config" />

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiProxyTarget = process.env.NOVISCOPE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
  server: {
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
```

- [ ] **Step 3: Create the test setup**

Create `web/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 4: Write the failing macro-phase contract test**

Create `web/src/lib/research-workbench.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { macroPhaseDefinitions, phaseForAgentId } from "./research-workbench";

describe("research workbench phases", () => {
  it("maps all nine agents into five ordered macro phases", () => {
    expect(macroPhaseDefinitions.map((phase) => phase.id)).toEqual([
      "demand_scope",
      "literature_gap",
      "hypothesis_idea",
      "experiment_verification",
      "paper_meeting",
    ]);
    expect(new Set(macroPhaseDefinitions.flatMap((phase) => phase.agentIds)).size).toBe(9);
    expect(phaseForAgentId("evidence_auditor")).toBe("experiment_verification");
  });
});
```

- [ ] **Step 5: Run the test and verify RED**

Run:

```bash
npm test -- src/lib/research-workbench.test.ts
```

Expected: FAIL because `research-workbench.ts` does not exist.

- [ ] **Step 6: Implement the phase definitions**

Create `web/src/lib/research-workbench.ts` with readonly definitions:

```ts
export type MacroPhaseId =
  | "demand_scope"
  | "literature_gap"
  | "hypothesis_idea"
  | "experiment_verification"
  | "paper_meeting";

export type MacroPhaseDefinition = {
  readonly id: MacroPhaseId;
  readonly agentIds: readonly string[];
  readonly primaryAgentId: string;
};

export const macroPhaseDefinitions: readonly MacroPhaseDefinition[] = [
  { id: "demand_scope", primaryAgentId: "demand_validator", agentIds: ["demand_validator", "research_refiner"] },
  { id: "literature_gap", primaryAgentId: "literature_scout", agentIds: ["literature_scout", "gap_analyst"] },
  { id: "hypothesis_idea", primaryAgentId: "idea_generator", agentIds: ["idea_generator"] },
  { id: "experiment_verification", primaryAgentId: "experiment_planner", agentIds: ["experiment_planner", "code_runner", "evidence_auditor"] },
  { id: "paper_meeting", primaryAgentId: "paper_meeting_writer", agentIds: ["paper_meeting_writer"] },
] as const;

export function phaseForAgentId(agentId: string): MacroPhaseId | null {
  return macroPhaseDefinitions.find((phase) => phase.agentIds.includes(agentId))?.id ?? null;
}
```

- [ ] **Step 7: Run tests and build**

Run:

```bash
npm test -- src/lib/research-workbench.test.ts
npm run build
```

Expected: phase test PASS; TypeScript and Vite build PASS.

- [ ] **Step 8: Commit**

```bash
git add DESIGN.md web/package.json web/package-lock.json web/vite.config.ts web/src/test/setup.ts web/src/lib/research-workbench.ts web/src/lib/research-workbench.test.ts
git commit -m "Add compact workbench design primitives"
```

---

### Task 2: Add Typed Workflow and Capability Clients

**Files:**
- Modify: `web/src/api/types.ts`
- Create: `web/src/api/workflow.ts`
- Create: `web/src/api/workflow.test.ts`
- Modify: `web/src/lib/research-workbench.ts`
- Modify: `web/src/lib/research-workbench.test.ts`

**Interfaces:**
- Produces: `getWorkflowCapabilities()`, `getWorkflowCanvasTemplate()`, `getWorkflowNextActions(questId)`.
- Produces: `WorkflowAgentCapability`, `WorkflowCanvasTemplate`, `WorkflowNextAction`, and `WorkflowNextActionsResponse`.
- Produces: `buildMacroPhaseViews(stages, capabilities)` returning exactly five `MacroPhaseView` records.
- Consumes: `/workflow/capabilities`, `/workflow/canvas-template`, and `/quests/{quest_id}/workflow-next-actions`.

- [ ] **Step 1: Write failing API-client tests**

Create `web/src/api/workflow.test.ts` and mock `globalThis.fetch` to return one fixture per path. Assert:

```ts
expect(await getWorkflowCapabilities()).toHaveLength(9);
expect((await getWorkflowNextActions("quest-1")).actions[0]?.action_type).toBe("review_stage");
expect((await getWorkflowCanvasTemplate()).core_flow_agent_ids).toHaveLength(5);
```

Also assert each request uses the `/api` prefix so Vite proxy and production routing stay consistent.

- [ ] **Step 2: Run the API tests and verify RED**

Run:

```bash
npm test -- src/api/workflow.test.ts
```

Expected: FAIL because `workflow.ts` and the response types do not exist.

- [ ] **Step 3: Add strict response types**

Add these unions and interfaces to `web/src/api/types.ts`:

```ts
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
```

- [ ] **Step 4: Implement the clients**

Create `web/src/api/workflow.ts`:

```ts
export async function getWorkflowCapabilities() {
  const response = await apiRequest<WorkflowCapabilitiesResponse>("/api/workflow/capabilities");
  return response.agents;
}

export function getWorkflowCanvasTemplate() {
  return apiRequest<WorkflowCanvasTemplate>("/api/workflow/canvas-template");
}

export function getWorkflowNextActions(questId: string) {
  return apiRequest<WorkflowNextActionsResponse>(`/api/quests/${questId}/workflow-next-actions`);
}
```

- [ ] **Step 5: Write the failing phase-view tests**

Extend `research-workbench.test.ts` with fixtures proving:

```ts
const phases = buildMacroPhaseViews(stages, capabilities);
expect(phases).toHaveLength(5);
expect(phases[0]?.primaryStage?.agent_id).toBe("demand_validator");
expect(phases[0]?.agents.find((agent) => agent.agentId === "research_refiner")?.status).toBe("planned");
expect(phases[3]?.agents.find((agent) => agent.agentId === "code_runner")?.canConfigureProvider).toBe(false);
```

- [ ] **Step 6: Implement the phase view model**

Add:

```ts
export type MacroPhaseAgentView = {
  readonly agentId: string;
  readonly displayName: string;
  readonly status: "implemented" | "planned";
  readonly canConfigureProvider: boolean;
};

export type MacroPhaseView = {
  readonly definition: MacroPhaseDefinition;
  readonly primaryStage: StageCard | null;
  readonly agents: readonly MacroPhaseAgentView[];
};
```

Build views only from API capability truth. If a capability is absent, represent the role as planned/unavailable; never infer it as runnable from the static phase list.

- [ ] **Step 7: Run frontend tests and backend contract tests**

Run:

```bash
npm test -- src/api/workflow.test.ts src/lib/research-workbench.test.ts
npm run build
cd .. && .venv/bin/python -m pytest -q tests/test_workflow_capabilities_api.py tests/test_workflow_canvas_api.py tests/test_workflow_next_actions_api.py tests/test_workflow_next_actions_late_stages_api.py
```

Expected: frontend tests PASS; backend workflow contract suites PASS.

- [ ] **Step 8: Commit**

```bash
git add web/src/api/types.ts web/src/api/workflow.ts web/src/api/workflow.test.ts web/src/lib/research-workbench.ts web/src/lib/research-workbench.test.ts
git commit -m "Add typed research workflow clients"
```

---

### Task 3: Build the Authoritative Next-Action Strip and Workbench Shell

**Files:**
- Create: `web/src/lib/workflow-action-view.ts`
- Create: `web/src/lib/workflow-action-view.test.ts`
- Create: `web/src/components/quest-next-action-strip.tsx`
- Create: `web/src/components/quest-next-action-strip.test.tsx`
- Modify: `web/src/pages/canvas-workspace.tsx`
- Modify: `web/src/api/quests.ts`
- Modify: `web/src/i18n/translations.ts`

**Interfaces:**
- Produces: `buildWorkflowActionView(action, language)` with localized title, reason, responsible party, and command kind.
- Produces: `QuestNextActionStrip` with `onRun(stageId, providerId?)` and navigation callbacks.
- Consumes: `WorkflowNextAction`, visible providers, `runStage(stageId, { provider_id })`, and typed translations.

- [ ] **Step 1: Write failing action-view tests**

Cover all five action types:

```ts
expect(buildWorkflowActionView(runAction, "zh").command).toBe("run");
expect(buildWorkflowActionView(reviewAction, "zh").title).toContain("人工复核");
expect(buildWorkflowActionView(configureAction, "en").command).toBe("open_providers");
expect(buildWorkflowActionView(waitAction, "zh").disabled).toBe(true);
```

Known blocking reasons must use translation keys. API `label` and `detail` are fallback evidence, not the primary Chinese copy.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
npm test -- src/lib/workflow-action-view.test.ts
```

Expected: FAIL because the view builder does not exist.

- [ ] **Step 3: Implement localized action views**

Use an exhaustive `switch` on `WorkflowActionType`. Return:

```ts
export type WorkflowActionCommand = "open_providers" | "open_stage" | "run" | "wait";

export type WorkflowActionView = {
  readonly command: WorkflowActionCommand;
  readonly disabled: boolean;
  readonly reason: string;
  readonly responsible: string;
  readonly title: string;
};
```

Add paired English/Chinese keys for action type, responsible agent/user, blocker reason, no-action state, provider override, and trust summary.

- [ ] **Step 4: Write the failing strip component tests**

Use Testing Library to assert:

- Only one heading with the next-action label is rendered.
- `run_stage` renders a provider selector containing visible personal and shared providers and calls `onRun(stageId, selectedProviderId)`.
- `review_stage` links to `/stages/{stage_id}?quest={quest_id}`.
- `configure_provider` links to `/providers`.
- `wait_for_stage` has no enabled primary command.
- Empty actions render the no-pending-action state.

- [ ] **Step 5: Implement `QuestNextActionStrip`**

Use a semantic `<section aria-labelledby>` with one primary command, one evidence/detail link, compact trust metadata, and a provider override `Select` only for runnable model-provider stages. Do not render a card grid inside the strip.

- [ ] **Step 6: Load authoritative action and capabilities in CanvasWorkspace**

Change the selected Quest loader to request in parallel:

```ts
Promise.all([
  getQuest(selectedQuestId),
  getQuestStages(selectedQuestId),
  getWorkflowNextActions(selectedQuestId),
  getWorkflowCapabilities(),
  getWorkflowCanvasTemplate(),
  getProviders(),
]);
```

After a stage run, refresh stages and next actions. Do not keep using `findNextActionStage` as the page-level authority.

- [ ] **Step 7: Rebuild the shell hierarchy**

Desktop: compact collapsible Quest rail plus one research surface. Mobile: replace the rail with a labeled Quest `<select>`. Place Quest identity and `QuestNextActionStrip` before the phase path. Remove the four summary cards and `ResearchCanvasDecisionBrief` from the default route.

- [ ] **Step 8: Run tests and build**

Run:

```bash
npm test -- src/lib/workflow-action-view.test.ts src/components/quest-next-action-strip.test.tsx
npm run build
```

Expected: tests and build PASS; no duplicate action heading in component tests.

- [ ] **Step 9: Commit**

```bash
git add web/src/lib/workflow-action-view.ts web/src/lib/workflow-action-view.test.ts web/src/components/quest-next-action-strip.tsx web/src/components/quest-next-action-strip.test.tsx web/src/pages/canvas-workspace.tsx web/src/api/quests.ts web/src/i18n/translations.ts
git commit -m "Add authoritative Quest next action"
```

---

### Task 4: Replace the Repeated Canvas Views with Macro Phases and Shared Inspector Tabs

**Files:**
- Create: `web/src/components/research-phase-path.tsx`
- Create: `web/src/components/research-phase-path.test.tsx`
- Create: `web/src/components/stage-workbench-tabs.tsx`
- Create: `web/src/components/stage-workbench-tabs.test.tsx`
- Modify: `web/src/components/research-canvas.tsx`
- Modify: `web/src/lib/research-canvas-data.ts`
- Modify: `web/src/i18n/translations.ts`
- Stop rendering: `web/src/components/research-canvas-decision-brief.tsx`
- Stop rendering: `web/src/components/research-canvas-overview.tsx`
- Stop rendering: `web/src/components/research-canvas-stage-map.tsx`
- Stop rendering: `web/src/components/research-canvas-inspector.tsx`

**Interfaces:**
- Produces: `ResearchPhasePath` controlled by `selectedPhaseId` and `onSelectPhase`.
- Produces: `StageWorkbenchTabs` shared by Canvas and Stage Detail.
- Consumes: `MacroPhaseView`, selected primary `StageCard`, capability status, provider readiness, and existing stage output/review/artifact components.

- [ ] **Step 1: Write failing phase-path tests**

Assert:

```ts
expect(screen.getAllByRole("button", { name: /phase/i })).toHaveLength(5);
expect(screen.getByText("Code Runner")).toHaveTextContent("Planned");
expect(screen.getByText("Evidence Auditor")).toHaveAttribute("aria-disabled", "true");
```

Also test arrow-key movement, selected phase state, next-action phase highlight, and vertical mobile DOM order. Do not assert pixel classes as behavior.

- [ ] **Step 2: Run phase tests and verify RED**

Run:

```bash
npm test -- src/components/research-phase-path.test.tsx
```

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement the five-phase path**

Render five real buttons in a responsive grid/stepper. Each phase shows one aggregate state, one salient signal, and agent-role chips. Planned chips are non-interactive text/status elements. The path receives the authoritative next action as a highlight only; it does not render a second action summary.

- [ ] **Step 4: Write failing shared-tab tests**

Test tab semantics and conditional availability:

- Overview always exists.
- Evidence exists when evidence or source data is present.
- Run exists for implemented roles.
- Review exists for stages with a review gate.
- Artifacts exists for output/artifact-capable stages.
- Advanced payload is collapsed by default.

Use `userEvent.click` and assert only the active `tabpanel` is visible.

- [ ] **Step 5: Implement `StageWorkbenchTabs`**

Define:

```ts
export type StageWorkbenchTabId = "overview" | "evidence" | "run" | "review" | "artifacts";

export type StageWorkbenchTabsProps = {
  readonly mode: "compact" | "full";
  readonly onRunStage: (stageId: string, providerId?: string) => void;
  readonly stage: StageCard;
  readonly stages: readonly StageCard[];
  readonly providerReadinessData: ProviderReadinessData;
};
```

Reuse existing stage output renderers and review controls. In compact mode, link to Stage Detail for destructive or verbose editing. Raw JSON remains inside a closed `<details>` element with an explicit Advanced label.

- [ ] **Step 6: Simplify `ResearchCanvas`**

The component should render only:

1. `ResearchPhasePath`.
2. `StageWorkbenchTabs` for the selected phase's primary stage.
3. A truthful empty/planned state if a phase has no runnable primary stage.

Remove local status filters and all repeated counter/decision/overview rendering. Preserve selected phase when stages refresh.

- [ ] **Step 7: Run component tests and build**

Run:

```bash
npm test -- src/components/research-phase-path.test.tsx src/components/stage-workbench-tabs.test.tsx
npm run build
```

Expected: tests and build PASS.

- [ ] **Step 8: Commit**

```bash
git add web/src/components/research-phase-path.tsx web/src/components/research-phase-path.test.tsx web/src/components/stage-workbench-tabs.tsx web/src/components/stage-workbench-tabs.test.tsx web/src/components/research-canvas.tsx web/src/lib/research-canvas-data.ts web/src/i18n/translations.ts
git commit -m "Rebuild Canvas around research phases"
```

---

### Task 5: Make New Quest a Progressive Intake

**Files:**
- Modify: `web/src/lib/quest-intake.ts`
- Create: `web/src/lib/quest-intake.test.ts`
- Create: `web/src/components/quest-context-fields.tsx`
- Create: `web/src/components/quest-context-fields.test.tsx`
- Modify: `web/src/pages/create-quest.tsx`
- Modify: `web/src/i18n/translations.ts`

**Interfaces:**
- Produces: `deriveQuestTitle(formState, language)` and `hasAdditionalQuestContext(formState)`.
- Preserves: `buildInitialDirection(formState, language)` as the complete structured backend payload.
- Consumes: existing `createQuest({ title, initial_direction })` without changing the backend request.

- [ ] **Step 1: Write failing intake tests**

Add cases:

```ts
expect(deriveQuestTitle({ ...emptyIntake, direction: "Use CV to analyze badminton actions." }, "en"))
  .toBe("Use CV to analyze badminton actions");
expect(deriveQuestTitle({ ...emptyIntake, title: "Custom title", direction: "Direction" }, "en"))
  .toBe("Custom title");
expect(hasAdditionalQuestContext(emptyIntake)).toBe(false);
expect(buildInitialDirection(emptyIntake, "zh")).toContain("进入实验前应先人工复核");
```

Clamp derived titles to 80 characters after whitespace normalization.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
npm test -- src/lib/quest-intake.test.ts
```

Expected: FAIL because the helper functions do not exist.

- [ ] **Step 3: Implement the intake helpers**

Keep direction required. Make the title optional in the UI and derive a backend-safe title at submit time. Keep all optional fields in `buildInitialDirection`, including explicit `Not provided`/`未提供`, so downstream agents receive a stable structure.

- [ ] **Step 4: Write failing progressive-disclosure tests**

Test `QuestContextFields`:

- Additional context fields are hidden initially.
- The `Add research context` button exposes reality and experiment groups.
- Existing example data opens the section automatically.
- All controls retain visible labels.

- [ ] **Step 5: Implement the progressive form**

The first viewport contains direction, optional title, output language, example actions, and Create Quest. Move scenario, demand evidence, target user, target, pain point, known work, data assets, metric, and expected output into `QuestContextFields`.

Use a sticky desktop preview and a mobile `<details>` preview. Do not put the preview in a nested card. Submit with:

```ts
await createQuest({
  initial_direction: buildInitialDirection(formState, language),
  title: deriveQuestTitle(formState, language),
});
```

Navigate to `/canvas?quest=${quest.id}` rather than the legacy root redirect.

- [ ] **Step 6: Run tests and build**

Run:

```bash
npm test -- src/lib/quest-intake.test.ts src/components/quest-context-fields.test.tsx
npm run build
```

Expected: tests and build PASS.

- [ ] **Step 7: Commit**

```bash
git add web/src/lib/quest-intake.ts web/src/lib/quest-intake.test.ts web/src/components/quest-context-fields.tsx web/src/components/quest-context-fields.test.tsx web/src/pages/create-quest.tsx web/src/i18n/translations.ts
git commit -m "Simplify New Quest intake"
```

---

### Task 6: Redesign Provider Settings Around Scope and Capabilities

**Files:**
- Create: `web/src/lib/provider-settings-view.ts`
- Create: `web/src/lib/provider-settings-view.test.ts`
- Create: `web/src/components/provider-scope-tabs.tsx`
- Create: `web/src/components/agent-assignment-matrix.tsx`
- Create: `web/src/components/agent-assignment-matrix.test.tsx`
- Modify: `web/src/pages/provider-settings.tsx`
- Modify: `web/src/components/provider-list-card.tsx`
- Modify: `web/src/components/provider-form-card.tsx`
- Stop rendering: `web/src/components/agent-assignment-card.tsx`
- Modify: `web/src/i18n/translations.ts`

**Interfaces:**
- Produces: provider scope filtering and capability-aware assignment rows.
- Produces: one page-level save command for dirty shared defaults.
- Consumes: visible provider records, agent assignments, workflow capabilities, current user role.
- Does not create a personal assignment endpoint. Personal providers remain run-time overrides in `QuestNextActionStrip` and Stage Detail.

- [ ] **Step 1: Write failing provider view-model tests**

Assert:

```ts
expect(filterProviders(providers, "personal").every((provider) => provider.scope === "personal")).toBe(true);
expect(buildAssignmentRows(assignments, capabilities).find((row) => row.agentId === "code_runner")?.editable).toBe(false);
expect(buildAssignmentRows(assignments, capabilities).find((row) => row.agentId === "demand_validator")?.status).toBe("implemented");
```

Also test dirty-row detection and that only changed implemented assignments become update requests.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
npm test -- src/lib/provider-settings-view.test.ts
```

Expected: FAIL because the view model does not exist.

- [ ] **Step 3: Implement provider view helpers**

Define `ProviderScopeTab = "shared" | "personal"`, `AgentAssignmentRow`, `buildAssignmentRows`, `buildAssignmentUpdates`, and `filterProviders`. Planned roles always return `editable: false` and `providerRequirement: "not_implemented"`.

- [ ] **Step 4: Write failing assignment-matrix tests**

Test:

- Nine rows render.
- Four planned roles show a Planned badge and disabled controls.
- Members see effective shared defaults but no save controls.
- Admin changes two rows and one page-level Save invokes two updates.
- A partial failure reloads server state and reports the failed agent IDs without claiming all changes saved.

- [ ] **Step 5: Implement scope tabs and the assignment matrix**

`ProviderScopeTabs` filters credentials. `AgentAssignmentMatrix` replaces repeated cards with a semantic table on desktop and labeled rows on mobile. Shared assignment editing is admin-only. Personal tab copy states that personal credentials are available as per-run overrides.

Implement Save using `Promise.allSettled` over dirty rows, then reload assignments. Report exact failed role names; never leave an unsynchronized success message.

- [ ] **Step 6: Update ProviderSettingsPage data loading**

Load providers, assignments, and capabilities together. Preserve create/edit/test provider behavior. Default tab is Personal for members and Shared for administrators; both tabs remain available when data exists.

- [ ] **Step 7: Run tests and backend provider contracts**

Run:

```bash
npm test -- src/lib/provider-settings-view.test.ts src/components/agent-assignment-matrix.test.tsx
npm run build
cd .. && .venv/bin/python -m pytest -q tests/test_provider_scope.py tests/test_providers.py tests/test_api.py -k "provider or agent_assignment"
```

Expected: frontend tests and provider API contract tests PASS.

- [ ] **Step 8: Commit**

```bash
git add web/src/lib/provider-settings-view.ts web/src/lib/provider-settings-view.test.ts web/src/components/provider-scope-tabs.tsx web/src/components/agent-assignment-matrix.tsx web/src/components/agent-assignment-matrix.test.tsx web/src/pages/provider-settings.tsx web/src/components/provider-list-card.tsx web/src/components/provider-form-card.tsx web/src/i18n/translations.ts
git commit -m "Redesign capability-aware provider settings"
```

---

### Task 7: Align Stage Detail with the Shared Workbench Hierarchy

**Files:**
- Modify: `web/src/pages/stage-detail.tsx`
- Modify: `web/src/components/stage-workbench-tabs.tsx`
- Modify: `web/src/components/stage-workbench-tabs.test.tsx`
- Modify: `web/src/components/stage-next-action-card.tsx`
- Modify: `web/src/i18n/translations.ts`

**Interfaces:**
- Reuses: `QuestNextActionStrip` action language and `StageWorkbenchTabs` full mode.
- Consumes: selected stage, complete workflow stages, `getWorkflowNextActions(questId)`, provider readiness, and `runStage(stageId, { provider_id })`.
- Preserves: review packet download, stage review controls, output rendering, artifact access, and advanced editor.

- [ ] **Step 1: Extend shared-tab tests for full mode**

Assert full mode includes review controls, complete output components, artifact download actions, and a collapsed Advanced editor. Add a regression asserting Next Action appears before the first tablist in DOM order.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
npm test -- src/components/stage-workbench-tabs.test.tsx
```

Expected: FAIL because Stage Detail has not adopted full workbench mode.

- [ ] **Step 3: Reorder Stage Detail**

Extend the existing loader from:

```ts
Promise.all([getQuest(questId), getQuestStages(questId)])
```

to:

```ts
Promise.all([
  getQuest(questId),
  getQuestStages(questId),
  getWorkflowNextActions(questId),
  getProviders(),
])
```

Store `nextActions.actions[0] ?? null` and refresh both stages and next actions after a
run or review mutation. Pass the loaded action into `StageNextActionCard`; do not derive
it from `getStageRunGate`.

Render in this order:

1. Compact stage/Quest identity header.
2. Authoritative stage action and blocker state with optional per-run provider selector.
3. `StageWorkbenchTabs mode="full"`.
4. Success/error live regions.
5. Advanced editor inside a closed `<details>` section.

Remove the standalone sequence of Review, Provider, Output, Next Action, and Editor cards. Keep their behavior through the shared tabs and existing child components.

- [ ] **Step 4: Make `StageNextActionCard` presentational**

Change `StageNextActionCard` to accept the already-loaded `WorkflowNextAction | null`,
the visible provider list, and run/navigation callbacks. Reuse
`buildWorkflowActionView`; remove its `getStageRunGate` import and all local action
selection. Stage Detail remains its only caller and therefore presents the same backend
action truth as Canvas without duplicating the decision algorithm.

- [ ] **Step 5: Run tests and build**

Run:

```bash
npm test -- src/components/stage-workbench-tabs.test.tsx src/components/quest-next-action-strip.test.tsx
npm run build
```

Expected: tests and build PASS.

- [ ] **Step 6: Commit**

```bash
git add web/src/pages/stage-detail.tsx web/src/components/stage-workbench-tabs.tsx web/src/components/stage-workbench-tabs.test.tsx web/src/components/stage-next-action-card.tsx web/src/i18n/translations.ts
git commit -m "Align stage detail with research workbench"
```

---

### Task 8: Complete Integrated, Responsive, Accessibility, and Visual QA

**Files:**
- Create: `scripts/seed_workbench_e2e.py`
- Create: `tests/e2e_support/fake_openai_provider.py`
- Create: `web/playwright.config.ts`
- Create: `web/e2e/compact-workbench.spec.ts`
- Modify: `web/src/components/quest-next-action-strip.tsx`
- Modify: `web/src/components/research-phase-path.tsx`
- Modify: `web/src/components/stage-workbench-tabs.tsx`
- Modify: `web/src/components/research-canvas.tsx`
- Modify: `web/src/pages/canvas-workspace.tsx`
- Modify: `web/src/pages/create-quest.tsx`
- Modify: `web/src/pages/provider-settings.tsx`
- Modify: `web/src/pages/stage-detail.tsx`
- Modify: `web/src/i18n/translations.ts`
- Update: `README.md`
- Update: `README.zh-CN.md`

**Interfaces:**
- Verifies the completed user flow through real browser surfaces.
- Consumes a disposable SQLite NoviScope instance seeded by `scripts/seed_workbench_e2e.py` and a local OpenAI-compatible fake at `http://127.0.0.1:8999/v1`.
- Produces screenshots and QA evidence outside tracked source under `.omo/evidence/compact-canvas-workbench/`.

- [ ] **Step 1: Create the deterministic E2E support services**

Create `tests/e2e_support/fake_openai_provider.py` as a small FastAPI app with:

- `GET /v1/models`, returning `{"data": [{"id": "noviscope-e2e-model"}]}`.
- `POST /v1/chat/completions`, returning one OpenAI-compatible choice whose message
  content is a JSON string accepted by `DemandValidationOutput`.
- A medium-confidence `go_with_human_review` result, explicit unverified evidence, and
  no invented experiment result.

Create `scripts/seed_workbench_e2e.py` with CLI arguments `--database-url` and
`--provider-base-url`. It must create the schema and then seed exactly:

- Admin: `admin.e2e@example.test` / `NoviScope-e2e-admin-2026`.
- Member: `member.e2e@example.test` / `NoviScope-e2e-member-2026`.
- One active shared OpenAI-compatible provider and one active member-owned personal
  provider, both using model `noviscope-e2e-model`, key `local-e2e-key`, and the supplied
  fake-provider base URL.
- A shared `demand_validator` assignment.
- One member-owned badminton-analysis Quest with its five initial stages pending.

The script must reject non-SQLite URLs, refuse to seed a database containing users,
and print non-secret seeded IDs as JSON. Unit-test its idempotency refusal and seeded
ownership in `tests/test_workbench_e2e_seed.py`.

- [ ] **Step 2: Add the Playwright configuration**

Create `web/playwright.config.ts` with an explicit external-server contract:

```ts
import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.NOVISCOPE_E2E_BASE_URL;

if (!baseURL) {
  throw new Error("NOVISCOPE_E2E_BASE_URL must point to a running NoviScope Web instance");
}

export default defineConfig({
  testDir: "./e2e",
  outputDir: "../.omo/evidence/compact-canvas-workbench/test-results",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "mobile",
      use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 } },
    },
    {
      name: "tablet",
      use: { ...devices["Desktop Chrome"], viewport: { width: 768, height: 1024 } },
    },
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } },
    },
  ],
});
```

The test configuration must not start production services. The execution command supplies
`NOVISCOPE_E2E_BASE_URL`, while Vite continues to proxy `/api` to
`NOVISCOPE_API_PROXY_TARGET`.

- [ ] **Step 3: Write the end-to-end scenarios**

Create tests for:

1. Login and select a Quest.
2. Confirm the next action is visible in the first viewport and appears once.
3. Navigate all five phases and inspect all nine role chips.
4. Confirm planned Code Runner and Evidence Auditor controls are disabled.
5. Run a runnable stage with a selected personal provider override.
6. Open review and evidence tabs and follow the Stage Detail link.
7. Create a direction-only Quest and confirm derived title and demand-review notice.
8. Filter Shared/Personal providers and verify member/admin assignment permissions.
9. Switch Chinese/English and confirm no missing key or overflowing command label.

Import `AxeBuilder` from `@axe-core/playwright` and run an accessibility scan after the
Canvas, New Quest, Provider Settings, and Stage Detail scenarios. Fail on `critical`
or `serious` violations. Use role and accessible-name locators; do not couple tests to
Tailwind class strings.

- [ ] **Step 4: Start the disposable stack and run automated verification**

Prepare and seed from the repository root:

```bash
mkdir -p .omo/e2e .omo/evidence/compact-canvas-workbench
rm -f .omo/e2e/compact-workbench.db
NOVISCOPE_PROVIDER_SECRET_KEY=noviscope-e2e-provider-key-0123456789-ABCD \
  .venv/bin/python scripts/seed_workbench_e2e.py \
  --database-url sqlite:///./.omo/e2e/compact-workbench.db \
  --provider-base-url http://127.0.0.1:8999/v1
```

Terminal 1, repository root:

```bash
.venv/bin/python -m uvicorn fake_openai_provider:app --app-dir tests/e2e_support --host 127.0.0.1 --port 8999
```

Terminal 2, repository root:

```bash
NOVISCOPE_DATABASE_URL=sqlite:///./.omo/e2e/compact-workbench.db \
NOVISCOPE_PROVIDER_SECRET_KEY=noviscope-e2e-provider-key-0123456789-ABCD \
NOVISCOPE_SESSION_SECRET_KEY=noviscope-e2e-session-key-0123456789-ABCDE \
NOVISCOPE_SESSION_COOKIE_SECURE=false \
  .venv/bin/python -m uvicorn noviscope.main:app --host 127.0.0.1 --port 8000
```

Terminal 3, `web/`:

```bash
NOVISCOPE_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 4173
```

Terminal 4, repository root:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
npm --prefix web test
npm --prefix web run build
NOVISCOPE_E2E_BASE_URL=http://127.0.0.1:4173 \
NOVISCOPE_E2E_ADMIN_EMAIL=admin.e2e@example.test \
NOVISCOPE_E2E_ADMIN_PASSWORD=NoviScope-e2e-admin-2026 \
NOVISCOPE_E2E_MEMBER_EMAIL=member.e2e@example.test \
NOVISCOPE_E2E_MEMBER_PASSWORD=NoviScope-e2e-member-2026 \
  npm --prefix web run test:e2e
```

Expected: backend tests, Ruff, frontend tests, production build, and Playwright scenarios all PASS. Existing dependency warnings may be reported but not hidden.

- [ ] **Step 5: Perform real-browser visual QA**

At 390x844, 768x1024, and 1440x1000, capture and inspect:

- Canvas with runnable next action.
- Canvas with human-review blocker.
- Canvas with planned experiment roles.
- New Quest collapsed and expanded context.
- Provider Shared and Personal tabs.
- Stage Detail Overview, Evidence, Review, and Advanced states.

Acceptance checks:

- Primary action visible without scrolling.
- No horizontal page overflow.
- No overlapping labels, controls, badges, or tabs.
- Mobile default does not stack every inspector section open.
- Keyboard focus order follows Quest selector, next action, phases, then inspector.
- Every mobile action target is at least 44px.
- Planned capability status is readable without color.
- No browser console errors or unhandled promise rejections.

- [ ] **Step 6: Inspect accessibility and layout diagnostics**

Review the Axe results emitted by Step 3 and use Playwright assertions to verify
`document.documentElement.scrollWidth <= document.documentElement.clientWidth` for
each route and viewport. Inspect React warnings and browser console output; any serious
Axe violation, horizontal overflow, missing list key, invalid DOM nesting, or unhandled
promise rejection returns to the task that owns the named component in the Files list
above.

- [ ] **Step 7: Update user documentation**

Document in both READMEs:

- Canvas as the default research workbench.
- Five macro phases and nine capability roles.
- Planned roles are visible but not runnable.
- Shared provider defaults versus personal per-run override.
- Direction-only Quest creation and mandatory demand review.

- [ ] **Step 8: Re-run the complete verification after QA fixes**

Repeat Step 4 and re-capture only screens affected by fixes. `git diff --check` must pass and `git status --short` must contain no generated screenshots, databases, cookies, traces, or build artifacts.

- [ ] **Step 9: Commit**

```bash
git add scripts/seed_workbench_e2e.py tests/e2e_support/fake_openai_provider.py tests/test_workbench_e2e_seed.py web/playwright.config.ts web/e2e/compact-workbench.spec.ts web/src README.md README.zh-CN.md
git commit -m "Verify compact Canvas workbench experience"
```

---

## Final Review and Handoff

After Task 8:

1. Run `superpowers:verification-before-completion` with fresh full outputs.
2. Run `omo:review-work` across goal/constraints, real QA, code quality, security, and repository context.
3. Record three runtime debugging hypotheses and evidence, including duplicate action authority, provider-scope leakage, and mobile inspector overflow.
4. Inspect the full branch diff and confirm only workbench-related files changed.
5. Push the feature branch and open or update a PR only when the user has authorized the GitHub write.
6. Do not merge the PR or resolve review threads without explicit user approval.
