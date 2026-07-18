# Coding Rules

- Keep AST parsing and taint logic deterministic, exact, and hallucination-free. A structural finding is a binary fact: a data-flow path exists in the syntax tree or it does not.
- Do not make LLM calls in `skill_passport_core/ast_tracer.py` or `skill_passport_core/classifier.py`.
- LLM use begins only in `skill_passport_core/reasoner.py`, through the locally authenticated Codex CLI.
- `reasoner.py` must invoke Codex CLI via subprocess, never the OpenAI API directly; no API key should be required anywhere in this project.
- Keep `skill_passport_core/` UI-agnostic. `cli.py` and `web/backend/main.py` must both import the core package and must not duplicate its logic.
- Never implement an auto-install or auto-execute path under any circumstance. The install command is a copy-paste reference only, shown for `verified` or `review` and hidden for `high_risk`.
- Keep the web application to exactly two pages: landing page and analysis page.
- Build and pass one Behavior Profile object to both classifier and reasoner before reasoning begins.
- Ground every Codex explanation and follow-up answer in the evidence objects passed to it. The reasoner must never invent a finding that is not present in the traced evidence.
- Preserve the distinction between `DISCLOSED`, `UNDISCLOSED`, and `CONTRADICTION`; disclosed telemetry must not be treated as an undisclosed or contradictory network call merely because it uses the network.
- Keep the core stateless: no user accounts, database, persistent history, or dependency-chain/repository-history analysis.
- Use exactly three fixtures: one real small skill from `github.com/anthropics/skills`, one synthetic disclosed-telemetry skill, and one synthetic contradiction skill.
- Use only `verified`, `review`, and `high_risk` as trust levels. Do not introduce `safe` or `caution`.
- Do not expand scope with repository drift/timeline analysis, dependency-chain trust analysis, or required side-by-side comparison.

