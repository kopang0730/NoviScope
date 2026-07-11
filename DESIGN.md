# NoviScope Design System

## 1. Atmosphere & Identity

NoviScope is a quiet research command center for lab-scale AI workflows. It should feel traceable, deliberate, and reviewable rather than flashy. The signature is a three-part research workbench: compact navigation, a clear current-quest brief, and a visible stage timeline that keeps evidence, blockers, and artifacts in one accountable loop.

## 2. Color

### Palette

| Role | Token | Light | Usage |
| --- | --- | --- | --- |
| Surface/canvas | `canvas` | `#f4f7f8` | App background |
| Surface/panel | `white` | `#ffffff` | Cards, forms, panels |
| Surface/subtle | `slate-50` | `#f8fafc` | Nested summaries, empty states |
| Text/primary | `ink` | `#12202f` | App-level text |
| Text/strong | `slate-900` | `#0f172a` | Headings and primary labels |
| Text/secondary | `slate-600` | `#475569` | Body copy and summaries |
| Text/muted | `slate-500` | `#64748b` | Metadata and hints |
| Border/default | `slate-200` | `#e2e8f0` | Cards and dividers |
| Border/input | `slate-300` | `#cbd5e1` | Form controls |
| Accent/primary | `teal-600` | `#0b766f` | Primary actions and active navigation |
| Accent/subtle | `teal-50` | `#effcfb` | Selected rows and soft highlights |
| Accent/focus | `teal-500` | `#0f8d86` | Focus rings |
| Status/success | `emerald-*` | Tailwind default | Complete states |
| Status/warning | `amber-*` | Tailwind default | Running/review-needed states |
| Status/error | `rose-*` | Tailwind default | Blocked/error states |
| Status/info | `sky-*` | Tailwind default | Provider/source metadata |

### Rules

- Teal is the only product accent. Use other colors only for semantic status.
- Keep the interface light and operational; avoid decorative gradients and large illustration areas.
- New color roles must be added here before they appear in UI code.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Tracking | Usage |
| --- | --- | --- | --- | --- | --- |
| Page title | 18px | 600 | 1.4 | 0 | Card and page headings |
| Section title | 16px | 600 | 1.45 | 0 | Quest/stage titles |
| Body | 14px | 400 | 1.5 | 0 | Primary UI copy |
| Label | 14px | 500 | 1.4 | 0 | Form labels and controls |
| Caption | 12px | 500 | 1.4 | 0 | Metadata, badges, hints |
| Overline | 11px | 600 | 1.3 | 0.04em | Small section labels |

### Font Stack

- Primary: `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
- Mono: system monospace only where code, identifiers, or artifact names need alignment.

### Rules

- Do not use hero-scale type inside the workspace.
- Keep all metadata compact and readable; no text below 12px for meaningful content.

## 4. Spacing & Layout

### Base Unit

All spacing derives from 4px.

| Token | Value | Usage |
| --- | --- | --- |
| `space-1` | 4px | Tight icon/label gaps |
| `space-2` | 8px | Badge and compact list spacing |
| `space-3` | 12px | Form and list item inner spacing |
| `space-4` | 16px | Default gaps between controls |
| `space-5` | 20px | Card padding on mobile |
| `space-6` | 24px | Card padding on desktop |
| `space-8` | 32px | Larger panel groups |

### Grid

- Max content width: 1440px.
- Workspace shell: sidebar plus main surface.
- Research workbench: left quest list, middle quest overview, right stage timeline/canvas.
- Breakpoints follow Tailwind defaults.

### Rules

- Prefer CSS grid for page-level panel layouts.
- Dense research panels may stack on smaller viewports; never force horizontal scrolling for the main workflow.

## 5. Components

### Card

- Structure: `<section>` with 8px radius, `slate-200` border, white background, and `shadow-panel`.
- Variants: default, warning/error by semantic border/background.
- Spacing: `space-5` mobile, `space-6` desktop.
- States: static container; repeated item cards may use hover only when clickable.
- Accessibility: card headings use visible text and semantic sectioning.

### Button

- Structure: inline-flex button or link styled through `buttonClassName`.
- Variants: primary teal, secondary white with border, ghost transparent.
- States: hover background shift, disabled opacity, visible teal focus ring, loading text.
- Accessibility: use `<button>` for actions and `<a>`/`Link` for navigation.

### Form Field

- Structure: label wrapping input/select/textarea plus optional hint/error.
- States: placeholder, focus ring, error text.
- Accessibility: visible labels are required.

### Badge

- Structure: compact rounded label.
- Variants: semantic tones only: gray, teal, green, amber, red, blue.
- Usage: status, confidence, provider/source tags.

### Research Workbench

- Structure: left quest list, middle overview, right workflow panel.
- States: loading, empty, selected, blocked, runnable, complete.
- Accessibility: quest rows are buttons with readable selected state; stages keep open links and run buttons separate.
- Motion: only transition color/background on interactive controls.

### Compact Research Workbench

- One authoritative next-action strip appears before workflow navigation.
- Desktop uses Quest rail, research surface, and contextual inspector.
- Mobile uses a Quest selector, sticky next action, vertical phase path, and collapsed inspector.
- Five macro phases contain nine agent roles; planned roles remain visible but disabled.
- The Canvas is workflow navigation, not a draggable workflow editor.

### Next Action Strip

- Structure: action type, responsible party, gate reason, trust summary, one primary action, and one secondary evidence or detail action.
- States: run agent, review evidence, resolve blocker, inspect output, and no pending action.
- Ownership: this is the only component that calculates and presents the primary next action; other surfaces may link to it but never repeat an action summary.
- Accessibility: primary and secondary controls have visible labels and 44px minimum touch targets on mobile.

### Macro Phase Path

- Structure: exactly five ordered phase nodes, each with a phase name, input-to-output statement, aggregate state, salient signal, and agent-role chips.
- States: pending, runnable, running, review required, blocked, complete, and planned extension.
- Planned roles: remain visible with a disabled `Planned` label and never appear runnable, complete, or provider-configurable.
- Interaction: selecting a phase updates the contextual inspector without navigating away; stage Run and Open actions remain separate controls.
- Layout: desktop uses a compact horizontal path; mobile uses a vertical path without horizontal scrolling.

### Stage Workbench Tabs

- Structure: contextual Overview, Evidence, Run, Review, and Artifacts tabs, shown only when meaningful for the selected phase.
- Advanced payloads and diagnostic JSON remain available in a collapsed Advanced section.
- States: tabs reflect available evidence, execution, review, and artifact data without duplicating the next-action summary.
- Accessibility: tab controls have readable selected state and 44px minimum touch targets on mobile.

### Research Result Summary

- Structure: a readable conclusion first, followed by compact decision signals, real-world context, evidence, uncertainty, and the next research action.
- Presentation: object keys, JSON braces, quoted values, and serialized payloads never appear in the primary result surface. Arrays render as short bullet lists and enumerated decisions render as localized labels or semantic badges.
- Trust: verified evidence and missing evidence remain visually distinct. Confidence never substitutes for source verification, and the result must keep human-review requirements visible.
- Detail: complete payloads and raw provider responses remain available only in the collapsed Advanced or audit sections.
- Layout: use dividers and unframed subsections inside one result surface instead of nesting several decorative cards. Two-column evidence layouts collapse to one column below the large breakpoint.
- Localization: Chinese and English labels, decision values, empty states, and explanatory copy ship together.

### Provider Matrix

- Structure: agent role, capability status, shared default model, connection state, and test action, organized in Shared and Personal views.
- States: implemented, requires review, planned, unavailable, connected, and unconfigured.
- Planned agent rows remain visible for roadmap clarity but disable assignment controls and explain why configuration is unavailable.
- Interaction: assignment changes use one page-level save action; provider tests remain explicit, accessible row-level actions.

### Workbench Constraints

- Do not duplicate action summaries outside the Next Action Strip.
- Do not nest top-level cards inside other top-level cards.
- Chinese and English copy ships together with equivalent meaning and behavior.
- Mobile primary controls use 44px minimum touch targets.

### Source Stage List

- Structure: compact key/value list using stage role labels and breakable stage IDs.
- Usage: generated outputs that depend on upstream stage payloads, including gap, experiment, and writing artifacts.
- States: empty state uses muted body text; populated state keeps labels bold and IDs selectable/readable.
- Accessibility: list items remain text, not badges, because users may need to copy source IDs for audits.

## 6. Motion & Interaction

| Type | Duration | Easing | Usage |
| --- | --- | --- | --- |
| Micro | 150ms | ease-out | Button/list hover |
| Standard | 200ms | ease-in-out | Tab and panel state changes |

### Rules

- Animate color, opacity, and transform only.
- Every clickable control needs hover/focus states.
- Keep motion restrained because the product is a research operations tool.

## 7. Depth & Surface

### Strategy

Mixed: thin borders define information boundaries; `shadow-panel` gives only top-level cards a soft lift.

| Level | Value | Usage |
| --- | --- | --- |
| Panel | `0 10px 30px rgba(15, 23, 42, 0.06)` | Main cards and sidebar |
| Nested | border plus `slate-50` | Summaries, previews, empty states |

### Rules

- Do not nest large cards inside large cards unless the inner element is a repeated item or a tool output preview.
- Avoid decorative shadows and colored glows.
