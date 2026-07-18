# Implementation Plan

## Day 1 — P0: fixtures, tracer foundation, and fetcher

- Create exactly three local test fixtures before the tracer is finished: one real small skill selected from `github.com/anthropics/skills`, one original synthetic `project-helper` skill with disclosed telemetry, and one original synthetic `auto-formatter` skill with contradicted network behavior.
- Push the two synthetic fixtures to small public repositories under the developer's GitHub account so they are fetched like real repositories.
- Create `skill_passport_core/fetcher.py` for GitHub REST API retrieval of README.md, SKILL.md, manifests, permission declarations, and source files.
- Create `skill_passport_core/ast_tracer.py` using Python's `ast` module.
- Implement source and sink recognition for the brief's initial categories: environment variables, file reads, credential paths, function arguments, network calls, subprocess/shell execution, file writes, and filesystem access outside declared scope.
- Emit exact file, line, and assignment-chain evidence.
- Add tracer tests against the three fixtures.

## Day 2 — P0: profile, classifier, and core validation

- Create `skill_passport_core/profile.py` to aggregate raw findings into the Behavior Profile.
- Create `skill_passport_core/classifier.py` to compare claims with profile categories and assign `CONTRADICTION`, `UNDISCLOSED`, or `DISCLOSED`.
- Validate the disclosed telemetry versus contradicted credential-flow distinction.
- Validate that the high-risk fixture explicitly identifies the denied network claim as a contradiction.
- Complete core output tests before building interface layers.

## Day 3 — P0/P1: Codex reasoner and CLI

- Create `skill_passport_core/reasoner.py` to invoke the locally authenticated Codex CLI through subprocess, using `codex exec --json --output-schema <schema-file> "<prompt>"` for the main judgment and translation call.
- Use `codex exec resume` for follow-up conversational Q&A, if P3 is implemented.
- Do not require an `OPENAI_API_KEY` or call the OpenAI API directly.
- Create `cli.py` as a thin wrapper over the core pipeline.
- Add streamed CLI stage output, Behavior Profile display, verdict block, follow-up prompt, and conditional install reference.
- Validate CLI output against all three fixtures.

## Day 4 — P2: FastAPI SSE backend and React web interface

- Create `web/backend/main.py` with the FastAPI SSE streaming endpoint.
- Stream fetching, parsing, tracing, profiling, classification, reasoning, profile, verdict, and error events using the shared core package.
- Create the React frontend under `web/frontend/`.
- Implement exactly two pages: landing page and analysis page.
- On the landing page, provide the headline, explainer, and single URL input that submits directly.
- On the analysis page, show stages, Behavior Profile, syntax-highlighted evidence, verdict card, conditional install copy button, and P3 follow-up box if time permits.

## Day 5 — P2/P3: local integration, demo validation, and submission readiness

- Run end-to-end checks locally for CLI and web against all three fixtures.
- Confirm the web presents the Behavior Profile before reasoning.
- Confirm stateless behavior, no database/auth/history, and no auto-install or auto-execution path.
- Confirm development, testing, and demo recording use an authenticated local Codex CLI session rather than a public deployment.
- Cut follow-up Q&A first if necessary; preserve the standalone verdict.
- Prepare the README's Codex/GPT-5.6 usage documentation and required session ID record.
- Prepare the under-three-minute demo video plan showing the built product and Codex/GPT-5.6 use.

