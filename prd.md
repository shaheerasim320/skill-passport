# Product Requirements Document

## Problem statement

AI coding agents install skills and MCP servers from GitHub with real filesystem, network, and shell permissions. A developer currently has to trust README.md or SKILL.md prose and cannot verify whether the repository's actual behavior matches its claims.

Skill Passport is an installation copilot that analyzes one public GitHub repository before installation, compares observed behavior with documented claims, explains the result in plain language, and never runs the installation itself.

## Target users

Solo developers and small teams using Codex, Claude Code, or similar tools who are about to install a third-party Agent Skill or MCP server from GitHub.

## Core features

### 1. Repository and claims fetch

The system accepts a public GitHub repository URL and fetches repository claims from README.md, SKILL.md, an MCP manifest, package.json, permission declarations, or other available sources of stated behavior. It also fetches source files representing actual behavior.

Acceptance criteria:

- A repository check can start from a public GitHub repository URL.
- The fetch stage reports the claims files and source files it found.
- The fetch stage uses the GitHub REST API.
- The system does not execute repository code or an install command.

### 2. Deterministic AST and taint tracing

The tracer parses Python source with Python's `ast` module. It identifies sensitive-data sources, effectful sinks, and variable-assignment taint paths. A finding includes exact file, line, and assignment-chain evidence. JavaScript/TypeScript parsing is stretch scope.

Sources include environment-variable reads, file reads, credential paths, and function arguments. Sinks include network calls, subprocess or shell execution, file writes, and filesystem access outside declared scope.

Acceptance criteria:

- Python files are parsed structurally, without an LLM call.
- Findings are binary structural facts: a path exists in the syntax tree or it does not.
- A detected path records its file, line number, and assignment chain.
- The tracer can distinguish no sensitive flow, disclosed telemetry, and credential-to-network flow using the three fixtures.

### 3. Behavior Profile

The system aggregates all raw findings into one structured Behavior Profile before classification or reasoning. The profile summarizes network, filesystem, secrets, and shell behavior, with detection state, evidence, and external domains where applicable.

Acceptance criteria:

- The profile is built from traced findings.
- The same profile object is passed to the classifier and reasoner.
- The profile is available as a standalone repository-behavior summary before the reasoning output.
- Empty categories remain represented with `detected: false` and an empty evidence list.

### 4. Claims classification

For each behavior category, the classifier compares the Behavior Profile with the claims text and assigns `CONTRADICTION`, `UNDISCLOSED`, or `DISCLOSED`.

Acceptance criteria:

- `CONTRADICTION` is used when claims explicitly deny behavior that the profile detects.
- `UNDISCLOSED` is used when the profile detects behavior and the claims say nothing about that category.
- `DISCLOSED` is used when claims mention detected behavior and the profile confirms it.
- The classifier is deterministic and makes no LLM calls.
- Disclosed telemetry is not classified as a contradiction or undisclosed behavior merely because it is a network call.

### 5. Codex reasoning, translation, and conversation

After classification, the reasoner receives the deterministic Behavior Profile and classification evidence. It judges concern in context, translates technical paths into plain English, and answers follow-up questions about the same evidence context. The reasoner invokes Codex CLI non-interactively through a subprocess; it does not call the OpenAI API directly.

Acceptance criteria:

- LLM use occurs only at the reasoner stage through Codex CLI.
- The main call uses `codex exec --json --output-schema <schema-file> "<prompt>"`.
- Follow-up Q&A uses `codex exec resume` and the same evidence context.
- Explanations cite or describe only evidence present in the passed profile and findings.
- Follow-up answers remain grounded in the same evidence context and do not invent findings.
- Follow-up Q&A is treated as P3 and may be cut if time is tight; the verdict remains complete without it.

### 6. Verdict and recommendation

The system produces a verdict with `trust_level` of `verified`, `review`, or `high_risk`, plus the Behavior Profile, evidence, and a one-line recommendation. `verified` means verified against observable behavior, not guaranteed secure.

Acceptance criteria:

- The verdict contains the trust level, profile, evidence, and recommendation.
- The three fixtures produce the expected trust levels: verified, review, and high_risk.
- The high-risk fixture is identified as `CONTRADICTION`, explicitly referencing the no-network claim.
- No verdict language overclaims static analysis as a security guarantee.

### 7. Install reference

The system displays the exact `npx skills add owner/repo` command as a copy-paste reference only when the trust level is `verified` or `review`. It adds a caveat for `review`, hides the command for `high_risk`, and never executes it.

Acceptance criteria:

- The install command is never automatically executed.
- The command is shown only for `verified` or `review`.
- The command is hidden for `high_risk`.

## Test fixtures

- Verified: one real small skill selected from `github.com/anthropics/skills`.
- Review: an original synthetic `project-helper` skill with explicitly disclosed anonymous telemetry.
- High risk: an original synthetic `auto-formatter` skill whose claims deny network access while its code sends an environment API key to an external domain.
- The two synthetic fixtures are pushed to small public repositories under the developer's GitHub account so the fetcher retrieves them like any public repository.

## Success criteria

- AST/taint tracing and classification are working before UI layers are built.
- All three fixtures are validated, including the disclosed-telemetry versus contradicted-credential-flow distinction.
- CLI output is complete and correct without relying on a UI.
- The web interface presents the same evidence and verdict through a landing page and an analysis page.
- The system remains stateless: one request in, one verdict out, with no accounts, database, or persistent history.
- No install or execution path exists.

