# Implementation Tracker

## To do

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



## Complete

- [x] Day 1: Create four fixtures: synthetic clean `text-formatter`, real `anthropics/skills` PDF filesystem fixture, synthetic disclosed-telemetry `project-helper`, and synthetic contradiction `auto-formatter`.
- [x] Day 1: Publish the synthetic fixtures under the developer's GitHub account: `text-formatter`, `project-helper`, and `auto-formatter`.
- [x] Day 1: Implement GitHub REST fetching in `skill_passport_core/fetcher.py`.
- [x] Day 1: Implement deterministic Python AST/taint tracing in `skill_passport_core/ast_tracer.py`.
- [x] Day 1: Add tracer tests for all four fixtures.
- [x] Day 2: Implement Behavior Profile aggregation in `skill_passport_core/profile.py`.
- [x] Day 2: Implement deterministic claims classification in `skill_passport_core/classifier.py`.
- [x] Day 2: Validate disclosed telemetry versus contradicted credential flow.
- [x] Day 3: Implement `skill_passport_core/reasoner.py` with Codex CLI subprocess calls.
- [x] Day 3: Add the `codex exec --json --output-schema <schema-file> "<prompt>"` main call.
- [x] Day 3: Confirm no direct OpenAI API call and no `OPENAI_API_KEY` requirement.
- [x] Day 3: Add `codex exec resume` follow-up support if P3 is implemented.
