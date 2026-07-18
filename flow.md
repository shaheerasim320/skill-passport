# User Flows

## Shared analysis state

```text
INPUT
  -> FETCHING
  -> PARSING
  -> TRACING
  -> PROFILE_BUILT
  -> CLASSIFYING
  -> REASONING
  -> VERDICT
  -> OPTIONAL_FOLLOW_UP
```

At `PROFILE_BUILT`, the deterministic Behavior Profile is available before Codex reasoning. The final state includes trust level, evidence, recommendation, and the conditional install reference.

## CLI journey

### 1. Command input

The user runs:

```text
skill-passport check <github-url>
```

The CLI validates the repository URL as the input to the shared analysis pipeline.

### 2. Streamed stage output

The CLI prints progress for fetching, parsing, tracing, profile construction, classification, and reasoning. It reports found claims/source files and deterministic findings with file and line evidence.

### 3. Behavior Profile

The CLI prints the repository behavior summary: network, filesystem, shell, and environment-secret behavior, plus external domains. This appears before the reasoning result.

### 4. Verdict block

The CLI prints `VERIFIED`, `REVIEW`, or `HIGH RISK`, the evidence-backed explanation, and a one-line recommendation.

### 5. Follow-up loop

The CLI prompts for a follow-up question. If the user asks one, `reasoner.py` resumes the Codex CLI conversation with `codex exec resume` and the same evidence context. The user can press Enter to continue or exit.

### 6. Install reference

For `verified`, the CLI shows the exact `npx skills add owner/repo` command. For `review`, it shows the command with a caveat. For `high_risk`, it hides the command. No command is executed.

## Web journey

The web application has exactly two pages.

### Page 1: Landing page

The page contains the Skill Passport headline, a one-paragraph explanation of disclosed, undisclosed, and contradiction behavior, and one GitHub URL input. Submission begins analysis directly; there is no separate launch-app click.

State transitions:

```text
EMPTY_INPUT -> URL_ENTERED -> SUBMITTED -> ANALYSIS_PAGE
```

### Page 2: Analysis page

The page receives the SSE stream and presents the same pipeline as the CLI:

1. Streaming stage list for fetching, parsing, tracing, profiling, classification, and reasoning.
2. Repository Behavior visualization from the Behavior Profile.
3. Syntax-highlighted evidence with file and line information.
4. Verdict card with trust level, explanation, and recommendation.
5. Conditional install command as a copy button for `verified` or `review`; hidden for `high_risk`.
6. Follow-up chat box using Codex CLI resume with the same evidence context, if P3 is implemented.

The profile is shown before the reasoning content. The web page restructures the CLI information visually but uses the same shared verdict logic.

