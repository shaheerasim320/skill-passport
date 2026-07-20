# Design System — Skill Passport Web UI

Source of truth: the two reference HTML/CSS files provided (landing page,
analysis page). Match these exactly — colors, typography, spacing, and
component structure — when building the real React implementation.

## Color tokens
| Token | Hex | Use |
|---|---|---|
| canvas | #0B0D10 | page background |
| surface-1 | #12151A | cards, panels |
| surface-2 | #191D24 | elevated surfaces, code blocks |
| border | #242932 | all hairline 1px borders |
| text-primary | #ECEEF1 | headings, primary copy |
| text-secondary | #8B93A0 | supporting copy |
| text-tertiary | #5C6470 | placeholders, disabled |
| seal (brand accent) | #C4A661 | logo, links, focus rings, stamp graphic — NEVER status |
| verified | #3FBF7F | VERIFIED status only |
| review | #F0A93C | REVIEW status only |
| high-risk | #E5484D | HIGH RISK status only |

## Typography
- Display (Fraunces serif): hero headline, large verdict word, guarantee
  statement only — never body copy.
- UI/body (IBM Plex Sans): nav, buttons, labels, card copy.
- Data/code (IBM Plex Mono): URLs, file paths, line numbers, commands,
  evidence snippets.

## Layout rules
- Landing page: exactly the sections in the reference file (header, hero,
  trust-level explainer, how-it-works steps, example evidence card,
  guarantee band, footer). Single URL input in the hero submits directly.
- Analysis page: two-column layout — fixed ~270px left pipeline rail,
  fluid right main column (max ~880px). Six pipeline stages: Fetching,
  Parsing, Tracing, Building Behavior Profile, Classifying, Reasoning.
- Cards: 1px hairline border, ~10-12px radius, no drop shadows —
  elevation via surface-level color only.
- Signature element: circular dashed-border "seal stamp" containing the
  verdict word, used small/static on landing trust cards, large/central
  on the analysis page verdict card.

## Behavior — real data replaces simulated data
The reference HTML uses a hardcoded JS timer to simulate the pipeline for
demo purposes. The real implementation must replace this entirely with
live SSE events from the FastAPI backend:
- Stage dots transition pending -> active -> complete as real SSE stage
  events arrive (not on a fixed timer).
- Behavior Profile card populates from the real profile SSE event.
- Verdict card populates from the real verdict SSE event, with the
  correct color/emoji/seal-stamp text for verified/review/high_risk.
- Evidence cards render actual findings (file, line, assignment chain)
  from the real analysis, not the hardcoded example.
- Claims-vs-behavior card shows the real quoted claim and real observed
  behavior text from the reasoner's output.
- Install command area follows the real conditional logic: shown for
  verified/review (review with caveat), hidden entirely for high_risk.
- Follow-up input, if implemented, sends real questions to the backend
  and displays real grounded answers.

## Non-negotiables from rules.md (do not violate while implementing this design)
- Exactly two pages: landing, analysis. No additional pages.
- Behavior Profile must render before the verdict/reasoning content.
- No auto-install — install command is copy-only, never executed.
- Stateless — no accounts, no persisted history.