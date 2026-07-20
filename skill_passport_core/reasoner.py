"""Grounded verdict translation through the locally authenticated Codex CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from skill_passport_core.ast_tracer import Finding, trace_python_files
from skill_passport_core.classifier import Classification, classify_behavior
from skill_passport_core.fetcher import FetchedFile, fetch_repository
from skill_passport_core.profile import BehaviorProfile, build_behavior_profile


SCHEMA_PATH = Path(__file__).with_name("verdict.json")
StageCallback = Callable[[str, dict[str, Any]], None]


class ReasonerError(RuntimeError):
    """Raised when the local Codex CLI cannot produce a structured verdict."""


@dataclass(frozen=True)
class CodexResponse:
    """A parsed Codex CLI result and its session identifier, when supplied."""

    output: dict[str, Any]
    thread_id: str | None


@dataclass(frozen=True)
class Verdict:
    trust_level: str
    behavior_profile: dict[str, Any]
    evidence: list[dict[str, Any]]
    classifications: list[dict[str, Any]]
    reasoning: dict[str, str]
    recommendation: str
    install_command: str
    thread_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_repository(
    github_url: str,
    timeout_seconds: float = 120.0,
    stage_callback: StageCallback | None = None,
) -> Verdict:
    """Run the read-only core pipeline for one public GitHub repository URL."""
    _notify(stage_callback, "fetching", {"target": github_url})
    repository = fetch_repository(github_url)
    _notify(
        stage_callback,
        "parsing",
        {
            "claims_files": [file.path for file in repository.claims_files],
            "source_files": [file.path for file in repository.source_files],
        },
    )
    findings = trace_python_files(repository.source_files)
    _notify(
        stage_callback,
        "tracing",
        {"source_file_count": len(repository.source_files), "findings": findings},
    )
    profile = build_behavior_profile(findings)
    _notify(
        stage_callback,
        "profiling",
        {"finding_count": len(findings), "behavior_profile": _profile_data(profile)},
    )
    claims_text = "\n\n".join(file.content for file in repository.claims_files)
    classifications = classify_behavior(profile, claims_text)
    _notify(
        stage_callback,
        "classifying",
        {"classifications": [asdict(item) for item in classifications]},
    )
    _notify(stage_callback, "reasoning", {})
    return reason_about(
        github_url=github_url,
        profile=profile,
        findings=findings,
        classifications=classifications,
        timeout_seconds=timeout_seconds,
    )


def analyze_fixture_folder(
    folder: str | Path,
    timeout_seconds: float = 120.0,
    stage_callback: StageCallback | None = None,
) -> Verdict:
    """Run the same core pipeline from a local fixture folder for manual checks."""
    fixture_path = Path(folder).resolve()
    if not fixture_path.is_dir():
        raise ValueError(f"Fixture folder does not exist: {fixture_path}")

    _notify(stage_callback, "fetching", {"target": str(fixture_path), "local": True})
    claims_files: list[FetchedFile] = []
    for path in fixture_path.rglob("*"):
        if path.is_file() and (
            path.name.lower().startswith("readme")
            or path.name.lower() in {"skill.md", "package.json", "manifest.json", "mcp.json"}
            or "permission" in path.name.lower()
        ):
            claims_files.append(
                FetchedFile(path=path.relative_to(fixture_path).as_posix(), content=path.read_text(encoding="utf-8"))
            )
    source_files = [
        FetchedFile(path=path.relative_to(fixture_path).as_posix(), content=path.read_text(encoding="utf-8"))
        for path in fixture_path.rglob("*.py")
    ]
    _notify(
        stage_callback,
        "parsing",
        {
            "claims_files": [file.path for file in claims_files],
            "source_files": [file.path for file in source_files],
        },
    )
    findings = trace_python_files(source_files)
    _notify(
        stage_callback,
        "tracing",
        {"source_file_count": len(source_files), "findings": findings},
    )
    profile = build_behavior_profile(findings)
    _notify(
        stage_callback,
        "profiling",
        {"finding_count": len(findings), "behavior_profile": _profile_data(profile)},
    )
    classifications = classify_behavior(
        profile, "\n\n".join(file.content for file in claims_files)
    )
    _notify(
        stage_callback,
        "classifying",
        {"classifications": [asdict(item) for item in classifications]},
    )
    _notify(stage_callback, "reasoning", {})
    return reason_about(
        github_url=str(fixture_path),
        profile=profile,
        findings=findings,
        classifications=classifications,
        timeout_seconds=timeout_seconds,
    )


def _notify(
    stage_callback: StageCallback | None, stage: str, data: dict[str, Any]
) -> None:
    """Emit optional UI progress without changing core analysis results."""
    if stage_callback is not None:
        stage_callback(stage, data)


def reason_about(
    *,
    github_url: str,
    profile: BehaviorProfile,
    findings: list[Finding],
    classifications: list[Classification],
    timeout_seconds: float = 120.0,
) -> Verdict:
    """Ask Codex for plain-English reasoning grounded in deterministic evidence."""
    profile_data = _profile_data(profile)
    evidence_data = [_finding_data(finding) for finding in findings]
    classification_data = [asdict(item) for item in classifications]
    trust_level = _trust_level(profile, classifications)
    prompt = _reasoning_prompt(
        github_url, trust_level, profile_data, evidence_data, classification_data
    )
    codex_response = _invoke_codex(prompt, timeout_seconds)
    model_output = codex_response.output

    reasoning = model_output.get("reasoning", {})
    if not isinstance(reasoning, dict):
        reasoning = {}
    judgment = _grounded_judgment(str(reasoning.get("judgment", "")), classifications)
    translation = str(reasoning.get("translation", ""))
    recommendation = str(model_output.get("recommendation", "")).strip()
    if not recommendation:
        recommendation = _default_recommendation(trust_level)

    return Verdict(
        trust_level=trust_level,
        behavior_profile=profile_data,
        evidence=evidence_data,
        classifications=classification_data,
        reasoning={"judgment": judgment, "translation": translation},
        recommendation=recommendation,
        install_command=_install_command(github_url, trust_level),
        thread_id=codex_response.thread_id,
    )


def answer_follow_up(
    question: str, thread_id: str | None, timeout_seconds: float = 120.0
) -> str:
    """Resume the established Codex thread without fetching or analyzing again."""
    if not thread_id:
        raise ReasonerError("No Codex thread is available for a follow-up question")
    if not question.strip():
        raise ValueError("Follow-up question cannot be empty")

    command = [
        "codex",
        "exec",
        "resume",
        thread_id,
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        question.strip(),
    ]
    completed = _run_codex(command, timeout_seconds)
    answer = _extract_answer_text(completed.stdout)
    if not answer:
        raise ReasonerError("Codex CLI did not return a follow-up answer")
    return answer


def _invoke_codex(prompt: str, timeout_seconds: float) -> CodexResponse:
    if not SCHEMA_PATH.is_file():
        raise ReasonerError(f"Verdict schema is missing: {SCHEMA_PATH}")
    command = [
        "codex",
        "exec",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        "--output-schema",
        str(SCHEMA_PATH),
        prompt,
    ]
    completed = _run_codex(command, timeout_seconds)
    output = _extract_codex_json(completed.stdout)
    if output is None:
        raise ReasonerError("Codex CLI did not return a JSON verdict")
    return CodexResponse(output=output, thread_id=_extract_thread_id(completed.stdout))


def _run_codex(command: list[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except FileNotFoundError as error:
        raise ReasonerError(
            "Codex CLI not found. Install it with: npm install -g @openai/codex, "
            "then run `codex login`. Skill Passport requires Codex CLI for the reasoning layer."
        ) from error
    except PermissionError as error:
        raise ReasonerError(
            "Codex CLI could not be executed because the operating system denied access"
        ) from error
    except OSError as error:
        raise ReasonerError(f"Codex CLI could not be started: {error}") from error
    except subprocess.TimeoutExpired as error:
        raise ReasonerError("Codex CLI reasoning timed out") from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or error.stdout.strip()
        raise ReasonerError(f"Codex CLI failed: {message}") from error

def _extract_codex_json(stdout: str) -> dict[str, Any] | None:
    """Extract the final schema-conforming JSON object from Codex JSONL output."""
    candidates: list[str] = [stdout.strip()]
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidates.extend(_event_text_candidates(event))

    for candidate in reversed(candidates):
        value = _parse_json_object(candidate)
        if value is not None:
            return value
    return None


def _extract_thread_id(stdout: str) -> str | None:
    """Read the thread_id emitted in Codex JSONL events without exposing it in prompts."""
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        thread_id = _find_thread_id(event)
        if thread_id:
            return thread_id
    return None


def _find_thread_id(value: Any) -> str | None:
    if isinstance(value, dict):
        thread_id = value.get("thread_id")
        if isinstance(thread_id, str) and thread_id.strip():
            return thread_id
        for child in value.values():
            found = _find_thread_id(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_thread_id(child)
            if found:
                return found
    return None


def _extract_answer_text(stdout: str | None) -> str | None:
    """Extract the final agent text from Codex JSONL follow-up output."""
    if not stdout:
        return None
    candidates: list[str] = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidates.extend(_event_text_candidates(event))
    for candidate in reversed(candidates):
        text = candidate.strip()
        if text and _parse_json_object(text) is None:
            return text
    return None


def _event_text_candidates(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for child in value for item in _event_text_candidates(child)]
    if isinstance(value, dict):
        candidates: list[str] = []
        for key in ("text", "output", "content", "message"):
            if key in value:
                candidates.extend(_event_text_candidates(value[key]))
        if "item" in value:
            candidates.extend(_event_text_candidates(value["item"]))
        return candidates
    return []


def _parse_json_object(value: str) -> dict[str, Any] | None:
    stripped = value.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _profile_data(profile: BehaviorProfile) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for name in ("network", "filesystem", "secrets", "shell"):
        category = profile.category(name)
        item: dict[str, Any] = {
            "detected": category.detected,
            "evidence": [_finding_data(finding) for finding in category.evidence],
        }
        if name == "network":
            item["external_domains"] = list(category.external_domains)
        data[name] = item
    return data


def _finding_data(finding: Finding) -> dict[str, Any]:
    return {
        "category": finding.category,
        "source": asdict(finding.source) if finding.source is not None else None,
        "sink": asdict(finding.sink),
        "assignment_chain": list(finding.assignment_chain),
        "external_domain": finding.external_domain,
    }


def _trust_level(
    profile: BehaviorProfile, classifications: list[Classification]
) -> str:
    if any(item.status == "CONTRADICTION" for item in classifications):
        return "high_risk"
    if any(profile.category(name).detected for name in ("network", "filesystem", "secrets", "shell")):
        return "review"
    return "verified"


def _reasoning_prompt(
    github_url: str,
    trust_level: str,
    behavior_profile: dict[str, Any],
    evidence: list[dict[str, Any]],
    classifications: list[dict[str, Any]],
) -> str:
    context = json.dumps(
        {
            "github_url": github_url,
            "trust_level": trust_level,
            "behavior_profile": behavior_profile,
            "evidence": evidence,
            "classifications": classifications,
        },
        indent=2,
    )
    return (
        "You are translating deterministic static-analysis evidence for a developer. "
        "Return JSON matching the supplied schema. Use only the evidence below; do not "
        "invent behavior, files, domains, or claims. In reasoning.judgment, explain the "
        "trust level in plain English. If a classification is CONTRADICTION, explicitly "
        "quote its claim_excerpt. If a behavior is DISCLOSED, state that it matches the "
        "repository documentation. reasoning.translation should concisely explain the "
        "observed path. Provide a one-line recommendation.\n\n"
        f"Deterministic evidence context:\n{context}"
    )


def _grounded_judgment(judgment: str, classifications: list[Classification]) -> str:
    contradiction_claims = [
        item.claim_excerpt for item in classifications if item.status == "CONTRADICTION" and item.claim_excerpt
    ]
    if not contradiction_claims:
        return judgment
    required_quote = contradiction_claims[0]
    if required_quote.lower() in judgment.lower():
        return judgment
    prefix = f'The repository claim "{required_quote}" is contradicted by the observed behavior. '
    return prefix + judgment


def _default_recommendation(trust_level: str) -> str:
    if trust_level == "high_risk":
        return "Do not install until the maintainer explains the contradiction."
    if trust_level == "review":
        return "Review the disclosed behavior against your organization’s policies before installing."
    return "The observable behavior matches the available claims; review before installing."


def _install_command(github_url: str, trust_level: str) -> str:
    if trust_level == "high_risk":
        return ""
    parts = github_url.rstrip("/").split("/")
    return f"npx skills add {parts[3]}/{parts[4]}" if len(parts) >= 5 else ""


def main(argv: list[str] | None = None) -> int:
    """Print a verdict for a GitHub URL or local fixture directory."""
    arguments = argv if argv is not None else sys.argv[1:]
    if len(arguments) != 1:
        print("Usage: python -m skill_passport_core.reasoner <github-url-or-fixture-folder>")
        return 2
    target = arguments[0]
    try:
        verdict = (
            analyze_repository(target)
            if target.startswith(("https://", "http://", "github.com/"))
            else analyze_fixture_folder(target)
        )
    except (ReasonerError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(verdict.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
