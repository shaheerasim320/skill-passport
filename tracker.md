# Implementation Tracker

## To do
- [ ] Record a public YouTube demonstration video (under three minutes).
- [ ] Submit `/feedback` from the main Codex project thread and save its Session ID.
- [ ] Confirm the current PyPI `pipx run` command works for judges.
- [ ] Complete the hackathon submission form with Developer Tools as the category.

## Hackathon submission checklist

- [x] Add an MIT license.
- [x] Document how Codex accelerated the work and which decisions and verification remained human-led.
- [x] Provide local CLI/web setup and judge testing instructions in the README.
- [ ] Record and upload the public demo video.
- [ ] Provide the repository URL and public video URL in the submission form.
- [ ] Provide the required Codex `/feedback` Session ID.

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
- [x] Day 3: Implement the thin CLI in `cli.py`.
- [x] Day 3: Reformat and visually validate CLI output against all fixtures.
- [x] Day 3: Implement and validate grounded Codex CLI follow-up Q&A.
- [x] Day 4: Implement and validate FastAPI SSE streaming in `web/backend/main.py`.
- [x] Day 4: Implement and validate the exactly-two-page React frontend in `web/frontend/`.
- [x] Day 4: Connect the frontend to live SSE analysis data and render real evidence, profile, verdict, error, install, and follow-up Q&A views.
- [x] Day 5: Prepare comprehensive README documentation for CLI, web, pipeline, configuration, safety, deployment, and future work.
- [x] Day 5: Run local end-to-end CLI and web validation against the fixture set.
- [x] Day 5: Confirm local-only authenticated Codex CLI operation for development, testing, and demo recording.
- [x] Day 5: Confirm safety and statelessness constraints.
- [x] Day 5: Add an MIT license and prepare the hackathon submission checklist.
