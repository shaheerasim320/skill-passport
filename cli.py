"""Terminal presentation layer for the read-only Skill Passport pipeline."""

from __future__ import annotations

import sys
import textwrap
import os
from typing import Any

from skill_passport_core.fetcher import FetchError
from skill_passport_core.reasoner import (
    ReasonerError,
    Verdict,
    answer_follow_up,
    analyze_fixture_folder,
    analyze_repository,
)


RULE = "──────────────────────────────────────────────"
DISPLAY_NAMES = {
    "network": "Network Access",
    "filesystem": "Filesystem Access",
    "shell": "Shell Execution",
    "secrets": "Environment Secrets",
}


def main(argv: list[str] | None = None) -> int:
    """Run ``skill-passport check <github-url>`` without executing the skill."""
    _configure_utf8_output()
    arguments = argv if argv is not None else sys.argv[1:]
    if len(arguments) != 2 or arguments[0] != "check":
        print("Usage: skill-passport check <github-url>")
        return 2

    target = arguments[1]
    try:
        verdict = _analyze(target)
    except (FetchError, ReasonerError, ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    _print_reasoning(verdict)
    _follow_up_loop(verdict)
    _print_install_reference(verdict)
    return 0


def _configure_utf8_output() -> None:
    """Allow the required box-drawing and status glyphs on Windows consoles."""
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except (AttributeError, OSError):
            # The terminal may not expose a classic Windows console handle.
            pass
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def _analyze(target: str) -> Verdict:
    normalized_target = (
        f"https://{target}" if target.startswith("github.com/") else target
    )
    if normalized_target.startswith(("https://", "http://")):
        return analyze_repository(normalized_target, stage_callback=_stage_output)
    return analyze_fixture_folder(target, stage_callback=_stage_output)


def _stage_output(stage: str, data: dict[str, Any]) -> None:
    if stage == "fetching":
        print("Fetching repository...")
        return
    if stage == "parsing":
        for path in data["claims_files"]:
            print(f"✓ Found {path}")
        source_count = len(data["source_files"])
        print(f"✓ Found {source_count} source {_plural('file', source_count)}")
        print("\nParsing source files...")
        python_files = sum(path.lower().endswith(".py") for path in data["source_files"])
        print(f"✓ Parsed {python_files} Python {_plural('file', python_files)}")
        return
    if stage == "tracing":
        print("\nTracing data flow...")
        findings = data["findings"]
        if not findings:
            print("✓ No sensitive data flows detected")
            return
        print(f"✓ Found {len(findings)} sensitive data flow(s)")
        for finding in findings:
            source = ""
            if finding.source is not None:
                source = f" from {finding.source.file}:{finding.source.line}"
            print(
                f"  ✓ {finding.category}: {finding.sink.file}:{finding.sink.line} "
                f"({finding.sink.description}){source}"
            )
        return
    if stage == "profiling":
        print("\nBuilding Repository Behavior Profile...")
        _print_behavior_profile_data(data["behavior_profile"])
        return
    if stage == "classifying":
        _print_claim_comparison_data(data["classifications"])
        return
    if stage == "reasoning":
        print("\nReasoning...")
        return


def _print_behavior_profile(verdict: Verdict) -> None:
    _print_behavior_profile_data(verdict.behavior_profile)


def _print_behavior_profile_data(behavior_profile: dict[str, Any]) -> None:
    print(RULE)
    print("Repository Behavior")
    print(RULE)
    for category in ("network", "filesystem", "shell", "secrets"):
        value = behavior_profile[category]
        print(f"{DISPLAY_NAMES[category]:<22}{_category_state(category, value)}")
    print("\nExternal Domains")
    domains = behavior_profile["network"].get("external_domains", [])
    print(", ".join(domains) if domains else "None")
    print(RULE)


def _category_state(category: str, value: dict[str, Any]) -> str:
    if not value["detected"]:
        return "Not Detected"
    count = len(value["evidence"])
    if category == "filesystem":
        return f"Detected ({count} file access finding(s))"
    if category == "network":
        return f"Detected ({count} finding(s))"
    return f"Detected ({count} finding(s))"


def _plural(word: str, count: int) -> str:
    return word if count == 1 else f"{word}s"


def _print_claim_comparison(verdict: Verdict) -> None:
    _print_claim_comparison_data(verdict.classifications)


def _print_claim_comparison_data(classifications: list[dict[str, Any]]) -> None:
    print("\nComparing repository claims...")
    if not classifications:
        print("✓ No undisclosed behavior detected")
        print("✓ No contradictions detected")
        return

    contradictions = [item for item in classifications if item["status"] == "CONTRADICTION"]
    for item in classifications:
        behavior = DISPLAY_NAMES[item["category"]].lower()
        if item["status"] == "DISCLOSED":
            print(f"✓ {behavior.capitalize()} matches repository claims")
        elif item["status"] == "UNDISCLOSED":
            print(f"✗ {behavior.capitalize()} is not disclosed in repository claims")
        else:
            print(f"✗ CONTRADICTION: {behavior} conflicts with repository claims")
            if item.get("claim_excerpt"):
                print(f"  Repository documentation states: \"{item['claim_excerpt']}\"")
    if not any(item["status"] == "UNDISCLOSED" for item in classifications):
        print("✓ No undisclosed behavior detected")
    if not contradictions:
        print("✓ No contradictions detected")


def _print_reasoning(verdict: Verdict) -> None:
    print(RULE)
    header = {
        "verified": "🟢 VERIFIED",
        "review": "🟡 REVIEW",
        "high_risk": "🔴 HIGH RISK",
    }[verdict.trust_level]
    print(header)
    print(RULE)
    _print_wrapped(verdict.reasoning.get("judgment", ""))
    translation = verdict.reasoning.get("translation", "")
    if translation:
        print()
        _print_wrapped(translation)
    print("\nRecommendation:")
    _print_wrapped(verdict.recommendation)
    print(RULE)


def _print_wrapped(value: str) -> None:
    print(textwrap.fill(value, width=64) if value else "No reasoning was returned.")


def _follow_up_loop(verdict: Verdict) -> None:
    while True:
        try:
            question = input("\nAsk a follow-up question, or press Enter to continue:\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not question:
            return
        try:
            print()
            _print_wrapped(answer_follow_up(question, verdict.thread_id))
        except (ReasonerError, ValueError) as error:
            print(f"Follow-up unavailable: {error}")


def _print_install_reference(verdict: Verdict) -> None:
    if verdict.trust_level == "high_risk":
        print("\nInstallation command hidden — repository classified HIGH RISK.")
        return
    print("\nRecommended install command:")
    if verdict.trust_level == "review":
        print("Note: this repository discloses behavior that should be reviewed before installing.")
    print(f"  {verdict.install_command}")
    print("\n(Copied manually by the developer. Skill Passport never")
    print("executes installations automatically.)")

if __name__ == "__main__":
    raise SystemExit(main())
