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

### Research Canvas

- Structure: compact summary counters, horizontally scrollable stage map, and a selected-stage inspector.
- States: selected stage, next action, pending review, runnable, blocked, complete.
- Evidence: every stage node may show up to four traceable facts; the inspector expands those facts with run state and review notes.
- Flow semantics: every stage node shows a compact input signal and output artifact pair so users can read the research workflow without knowing internal agent names.
- Traceability: the inspector shows saved output and evidence field counts before detailed evidence, making empty or blocked stages obvious.
- Accessibility: stage selection is a real button, while run/open actions remain separate controls.
- Layout: map stacks above the inspector on narrow screens and uses a fixed-width scroll region for the five-stage workflow.

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
