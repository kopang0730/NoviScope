# NoviScope Compact Canvas Workbench Design

**Status:** Approved information architecture, pending specification review
**Scope:** Web MVP information architecture and interaction redesign
**Audience:** Lab members, supervisors, and administrators using shared NoviScope

## 1. Objective

Redesign NoviScope's Web MVP around a compact research workbench. A user opening a
Quest must be able to answer, in the first viewport:

1. Where is this research effort in the workflow?
2. What is the single next action, and who should take it?
3. What evidence, review gate, or execution record makes the current state credible?

The product remains an operational research system, not a marketing dashboard and not
a free-form automation editor. The UI must support the current five runnable workflow
stages while honestly exposing the long-term nine-agent research team.

## 2. Problems in the Current Surface

The current Canvas has real functionality but distributes the same decision signal
across counters, a decision brief, an overview, a stage map, and an inspector. This
creates excessive vertical scrolling and forces users to infer the next action.

The current implementation also represents two different concepts as if they were one:

- A Quest currently creates five runnable stages: demand validation, literature scout,
  idea generation, experiment planning, and paper/meeting writing.
- The agent registry has nine roles. Research Refiner, Gap Analyst, Code Runner, and
  Evidence Auditor are planned capabilities, not runnable stages in the Web MVP.

The redesigned UI must not make planned automation look completed or runnable. It must
also avoid presenting the five-stage workflow as an inflexible limit once the remaining
agents are implemented.

## 3. Product Decisions

### 3.1 Five macro phases are the primary workflow

Users navigate the research lifecycle through five macro phases rather than internal
agent IDs:

| Macro phase | Research purpose | Current primary stage | Agent roles shown inside the phase |
| --- | --- | --- | --- |
| Demand and scope | Confirm a meaningful, bounded research problem. | Demand Validator | Demand Validator, Research Refiner |
| Literature and gap | Build a credible evidence map and identify limitations. | Literature Scout | Literature Scout, Gap Analyst |
| Hypothesis and idea | Select a falsifiable, evidence-linked contribution. | Idea Generator | Idea Generator |
| Experiment and verification | Plan, run, audit, and interpret experiments. | Experiment Planner | Experiment Planner, Code Runner, Evidence Auditor |
| Paper and meeting | Produce traceable drafts and review material. | Paper and Meeting Writer | Paper and Meeting Writer |

The macro phase is the user's navigation unit. The agent role is a capability inside the
phase. Each role carries an explicit capability status: `runnable`, `requires review`,
`planned`, or `unavailable`.

### 3.2 No free-form node graph in the MVP

NoviScope will use a structured, canvas-like research path rather than a draggable
node editor. The current workflow has ordered dependencies and human gates; allowing
users to draw arbitrary links would imply backend behavior that does not exist, add
layout persistence and mobile complexity, and obscure the formal evidence contract.

The Canvas is visual navigation and state inspection. It is not workflow programming.

### 3.3 One authoritative next-action surface

Only one component determines and presents the primary next action. It uses existing
workflow readiness, provider readiness, human-review state, and stage status. Summary
surfaces may link to this component but must not recompute or repeat a competing action.

## 4. Compact Canvas Workbench

### 4.1 Desktop layout

The desktop route uses a three-part workbench within the existing application shell:

| Area | Width and behavior | Content |
| --- | --- | --- |
| Quest rail | 240-280px, collapsible, sticky on desktop | Quest search, compact Quest list, create action |
| Research surface | Flexible primary column | Quest identity, next-action strip, macro-phase path |
| Inspector | 360-420px when a phase is selected | Overview, evidence, run, review, and artifact tabs |

The inspector may move below the phase path at narrower desktop widths. The application
must not introduce horizontal scrolling for the main research path.

### 4.2 Mobile layout

Mobile uses one task-focused column:

1. Compact Quest selector instead of a persistent Quest rail.
2. Sticky next-action strip beneath the global header.
3. Vertical five-phase stepper with clear status and no horizontal map.
4. Selected phase opens a bottom sheet or accordion inspector.
5. Evidence, raw payload, and secondary metadata remain collapsed until requested.

The first actionable control must appear without scrolling past a long dashboard summary.

### 4.3 Quest identity and next-action strip

The top of the research surface contains the Quest title, concise direction, Quest
status, and a single next-action strip.

The strip includes:

- Action type: `Run agent`, `Review evidence`, `Resolve blocker`, `Inspect output`, or
  `No pending action`.
- Responsible party: named agent, researcher, or supervisor.
- Reason: the precise gate, dependency, or evidence condition driving the action.
- Trust summary: evidence count, review status, and confidence when available.
- One primary action and one secondary evidence/detail action.

Examples:

- `Review real-world demand`: human review is required before literature and experiment
  work can advance.
- `Run Literature Scout`: demand review passed and a compatible provider is available.
- `Resolve experiment results`: paper claims cannot become formal until a trusted
  Code Runner result and Evidence Auditor approval exist.

### 4.4 Macro-phase path

The visual path contains exactly five phase nodes. Each node exposes:

- Phase name and short input-to-output statement.
- Aggregate state: pending, runnable, running, review required, blocked, complete, or
  planned extension.
- One salient signal, such as paper count, selected idea, required input, run status,
  or artifact readiness.
- A compact list of agent-role chips. Planned chips are visibly disabled and include a
  `Planned` label.

Selecting a node changes the inspector. It does not navigate away or require a separate
page load. Stage-specific Run and Open actions remain explicit controls, not clickable
card chrome.

### 4.5 Inspector tabs

The inspector is contextual and only displays meaningful tabs for the selected phase:

| Tab | Purpose |
| --- | --- |
| Overview | Goal, status, dependencies, inputs, outputs, and current blocker. |
| Evidence | Papers, sources, source quality, confidence, and traceability. |
| Run | Provider assignment, model, run state, logs, metrics, and execution provenance. |
| Review | Human approval, rejection, review notes, and historical decisions. |
| Artifacts | Research briefs, plans, paper drafts, meeting packet, and downloads. |

Raw JSON and diagnostic payloads move into a collapsed Advanced section. They remain
available to researchers without competing with the operational decision surface.

## 5. New Quest Intake

New Quest becomes a progressive intake rather than a long form.

### 5.1 Default intake

The default screen asks only for:

- Research direction in natural language. This is the required field and supports a
  supervisor's two or three sentence brief.
- Optional working title.
- Output language: Chinese, English, or bilingual.

Submission creates the Quest and explains the first safety gate: real-world demand must
receive human review before experimental work advances.

### 5.2 Expanded context

An expandable `Add research context` section accepts optional details without blocking
quick entry:

- Real-world demand source or enterprise context.
- Known papers, baselines, repositories, datasets, or benchmarks.
- Available data, code, GPU constraints, and privacy restrictions.
- Expected application scenario, evaluation metrics, and desired outputs.

Desktop shows a compact live research brief beside the form. Mobile shows the brief as
a collapsible preview after the required fields, not at the bottom of a long page.

## 6. Provider and Agent Assignment

Provider configuration becomes a capability-aware matrix rather than nine large cards.

### 6.1 Configuration modes

| Mode | Visibility | Who can edit |
| --- | --- | --- |
| Lab shared | Available to all lab users | Administrators |
| Personal override | Visible only to the owner | The current user |

The page uses two tabs, `Shared` and `Personal`, to organize provider credentials.
Shared providers may be assigned as lab-wide agent defaults by administrators.
Personal providers are selected as an explicit override when the owner runs a stage;
the MVP does not persist a separate personal default assignment for every agent.

### 6.2 Agent assignment matrix

Each row displays agent role, capability status, shared default model, connection
state, and a test action. Planned agents remain visible for roadmap clarity but disable
assignment controls and state why configuration is unavailable.

There is one page-level save action for changed assignments. Per-provider testing may
remain row-level, with an accessible label that names the provider and agent.
Members can view the effective shared default. When a runnable action is opened, they
may choose one of their own personal providers for that run without changing the lab
default.

## 7. Stage Detail Route

The full Stage Detail page adopts the same hierarchy as the Canvas inspector:

1. Next action and trust/blocker state.
2. Phase summary and primary output.
3. Evidence, run, review, and artifacts in tabs or ordered sections.
4. Advanced payload editor and diagnostic JSON at the bottom.

The route remains valuable for deep inspection, direct links, editing, and audit work.
The Canvas becomes the default navigation and control surface, not a replacement for
detail pages.

## 8. Data and State Contracts

The redesign must reuse existing backend data instead of inventing presentation-only
workflow truth.

| UI decision | Existing source of truth |
| --- | --- |
| Quest and stage state | Quest and StageCard APIs |
| Next action | workflow readiness, stage run gate, provider readiness, review state |
| Agent capability status | `/workflow/capabilities` |
| Provider assignment | shared agent defaults plus the stage-run `provider_id` override |
| Evidence and trust | stage output/evidence payload, evidence audit API, artifact endpoints |
| Review decision | human approval and review notes on the stage |

The UI must not claim that a planned agent ran, that an experiment exists without
trusted metrics, or that a draft is ready for formal claims without the evidence audit.

## 9. Accessibility and Internationalization

- Chinese and English are first-class translations; new labels use the existing i18n
  key system and both languages ship together.
- The phase path is keyboard navigable with clear selected, runnable, blocked, and
  disabled semantics.
- All primary actions retain visible text labels. Icon-only buttons require tooltips and
  accessible names.
- Touch targets are at least 44px where a mobile user must operate them.
- Planned agents are communicated with text and semantic state, not color alone.
- No state change relies only on hover, motion, or canvas position.

## 10. Visual System Changes

The existing quiet research-command-center style remains the visual contract:

- Keep the white, slate, and teal palette; reserve semantic amber, emerald, sky, and
  rose tones for status.
- Use one top-level panel per workbench region. Avoid nested card stacks.
- Use restrained 8px corners, thin borders, and compact operational typography.
- Avoid decorative gradients, hero treatments, or free-floating visual effects.
- Motion only clarifies selection, drawer transitions, and running state.

`DESIGN.md` must be updated before implementation to replace the current fixed
five-stage horizontal-map wording with the macro-phase, capability, and responsive
contracts in this document.

## 11. Implementation Boundaries

### Included in the future implementation plan

- Canvas workspace, research Canvas primitives, responsive layouts, and i18n strings.
- New Quest progressive disclosure and research brief preview.
- Provider Shared/Personal tabs and capability-aware assignment matrix.
- Stage Detail hierarchy alignment.
- API consumption for capability state and evidence audit state where endpoints already
exist.
- Component, interaction, accessibility, and visual QA coverage.

### Explicitly excluded

- GPU scheduling, Code Runner execution, baseline reproduction, and Evidence Auditor
  execution.
- New workflow-state backend semantics or arbitrary user-defined workflow graphs.
- Changing the formal evidence-audit trust contract.
- Third-party upload, data egress, or provider-security policy changes.

## 12. Acceptance Criteria

The implementation is acceptable when:

1. The current Quest, primary next action, responsible party, and reason are visible in
   the first viewport on desktop and mobile.
2. The default Canvas shows five macro phases, while all nine agent roles remain
   discoverable with truthful runnable/planned status.
3. No duplicated next-action decision surface appears in the Canvas.
4. The mobile Canvas uses a vertical path and collapsed inspector rather than a long
   stacked dashboard or horizontal map.
5. New Quest supports a direction-only start while preserving optional research context.
6. Provider settings distinguish shared defaults, personal run-time overrides, and
   planned capabilities without implying persistent personal agent assignments.
7. Existing evidence, review, and formal-claim blockers remain visible and cannot be
   visually downgraded to optional decoration.
8. Chinese and English strings, keyboard behavior, mobile touch targets, and visual
   layout are verified through real browser QA at desktop and mobile viewports.

## 13. Delivery Sequence

The implementation plan should split work into independently reviewable slices:

1. Update `DESIGN.md`, shared Canvas primitives, and i18n contracts.
2. Rebuild the Canvas workspace shell and next-action surface.
3. Introduce macro-phase path and inspector tabs using existing stage data.
4. Redesign New Quest and Provider Settings.
5. Align Stage Detail, then complete responsive, accessibility, and visual QA.

No frontend implementation begins until this specification has been reviewed by the
user and an implementation plan has been approved.
