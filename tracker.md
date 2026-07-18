# Implementation Tracker

## To do

- [ ] Day 1: Create the three local fixtures: one real small skill from `github.com/anthropics/skills`, plus synthetic `project-helper` and `auto-formatter` fixtures.
- [ ] Day 1: Push the two synthetic fixtures to small public repositories under the developer's GitHub account.
- [ ] Day 1: Implement GitHub REST fetching in `skill_passport_core/fetcher.py`.
- [ ] Day 1: Implement deterministic Python AST/taint tracing in `skill_passport_core/ast_tracer.py`.
- [ ] Day 1: Add tracer tests for all three fixtures.
- [ ] Day 2: Implement Behavior Profile aggregation in `skill_passport_core/profile.py`.
- [ ] Day 2: Implement deterministic claims classification in `skill_passport_core/classifier.py`.
- [ ] Day 2: Validate disclosed telemetry versus contradicted credential flow.
- [ ] Day 3: Implement `skill_passport_core/reasoner.py` with Codex CLI subprocess calls.
- [ ] Day 3: Add the `codex exec --json --output-schema <schema-file> "<prompt>"` main call.
- [ ] Day 3: Add `codex exec resume` follow-up support if P3 is implemented.
- [ ] Day 3: Confirm no direct OpenAI API call and no `OPENAI_API_KEY` requirement.
- [ ] Day 3: Implement the thin CLI in `cli.py`.
- [ ] Day 3: Validate CLI output against all fixtures.
- [ ] Day 4: Implement FastAPI SSE streaming in `web/backend/main.py`.
- [ ] Day 4: Implement the exactly-two-page React frontend in `web/frontend/`.
- [ ] Day 4: Add landing-page submission and analysis-page evidence/verdict views.
- [ ] Day 5: Run local end-to-end CLI and web validation.
- [ ] Day 5: Confirm local-only authenticated Codex CLI operation for development, testing, and demo recording.
- [ ] Day 5: Confirm safety and statelessness constraints.
- [ ] Day 5: Prepare README Codex/GPT-5.6 documentation, session ID record, and demo plan.

## In progress

- None.

## Complete

- None.

