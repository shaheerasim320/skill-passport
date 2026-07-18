# Technical Specification

## Stack

- Backend: Python and FastAPI.
- Core package: `skill_passport_core/`, imported by both entry points.
- GitHub fetcher: `skill_passport_core/fetcher.py` using the GitHub REST API.
- Static analysis: Python `ast` module in `skill_passport_core/ast_tracer.py`.
- Profile aggregation: `skill_passport_core/profile.py`.
- Deterministic classification: `skill_passport_core/classifier.py`.
- Reasoning: `skill_passport_core/reasoner.py`, invoking the locally authenticated Codex CLI through subprocess.
- Web frontend: React.
- Web transport: Server-Sent Events from the FastAPI backend.
- CLI: `cli.py`, a thin wrapper over the core package.

## Reasoner integration

`reasoner.py` must not call the OpenAI API directly and must not require an `OPENAI_API_KEY`. It invokes Codex CLI non-interactively for the main judgment and translation call:

```text
codex exec --json --output-schema <schema-file> "<prompt>"
```

The `<schema-file>` is the `schemas/verdict.json` definition represented in `schema.md` in this planning batch. Follow-up conversational Q&A uses `codex exec resume` and remains grounded in the existing evidence context.

## Stateless boundary and deployment

The service is stateless: one request in, one verdict out. No user accounts, authentication, database, persistent history, or persistent schema is required. The CLI and web backend must both import shared core logic and must not duplicate it.

Because `reasoner.py` depends on an authenticated local Codex CLI session, the project runs locally for development, testing, and demo recording rather than being deployed to a public host.

## SSE streaming endpoint contract

The web backend exposes one streaming analysis endpoint. The request supplies a public GitHub repository URL. The response is an SSE stream whose events report pipeline progress and then the structured analysis result.

Request shape:

```json
{
  "github_url": "https://github.com/owner/repo"
}
```

Event sequence:

1. Fetching repository claims and source files.
2. Parsing source files.
3. Tracing data flow.
4. Building the Behavior Profile.
5. Classifying behavior against claims.
6. Reasoning through Codex CLI.
7. Final verdict, or an error event if analysis cannot complete.

Each event is an SSE `data` payload conforming to the shape in `schema.md`. Progress events carry the current stage and human-readable status. The profile event carries the Behavior Profile before reasoning. The final event carries the Verdict. The stream then completes.

## GitHub REST API integration

`fetcher.py` uses the public GitHub REST API to retrieve a repository's claims sources and source files. Claims sources include README.md, SKILL.md, an MCP manifest, package.json, permission declarations, and other available sources of stated behavior. Source files are fetched for analysis.

The fetch stage reports found claims files and the number or set of source files available to parse. It must not execute fetched code, install dependencies, or run repository commands. The implementation should preserve repository path and line information needed by findings.

## Pipeline contract

```text
GitHub URL
  -> fetcher.py: claims + source files
  -> ast_tracer.py: raw deterministic findings
  -> profile.py: Behavior Profile
  -> classifier.py: category classifications
  -> reasoner.py: Codex CLI judgment, translation, conversation
  -> Verdict
```

The Behavior Profile is the single structured object passed to both classifier and reasoner.

