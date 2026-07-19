"""Deterministic aggregation of traced findings into a Behavior Profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from skill_passport_core.ast_tracer import Finding


BEHAVIOR_CATEGORIES = ("network", "filesystem", "secrets", "shell")


@dataclass(frozen=True)
class BehaviorCategory:
    detected: bool
    evidence: tuple[Finding, ...]
    external_domains: tuple[str, ...] = ()


@dataclass(frozen=True)
class BehaviorProfile:
    network: BehaviorCategory
    filesystem: BehaviorCategory
    secrets: BehaviorCategory
    shell: BehaviorCategory

    def category(self, name: str) -> BehaviorCategory:
        if name not in BEHAVIOR_CATEGORIES:
            raise ValueError(f"Unknown behavior category: {name}")
        return getattr(self, name)

    def to_dict(self) -> dict[str, dict[str, object]]:
        """Return the stable, JSON-ready shape used by later pipeline stages."""
        profile: dict[str, dict[str, object]] = {}
        for name in BEHAVIOR_CATEGORIES:
            category = self.category(name)
            value: dict[str, object] = {
                "detected": category.detected,
                "evidence": list(category.evidence),
            }
            if name == "network":
                value["external_domains"] = list(category.external_domains)
            profile[name] = value
        return profile


def build_behavior_profile(findings: Iterable[Finding]) -> BehaviorProfile:
    """Aggregate raw deterministic findings without inferring new behavior."""
    grouped: dict[str, list[Finding]] = {name: [] for name in BEHAVIOR_CATEGORIES}
    for finding in findings:
        if finding.category in grouped:
            grouped[finding.category].append(finding)

    categories: dict[str, BehaviorCategory] = {}
    for name, evidence in grouped.items():
        domains = tuple(
            dict.fromkeys(
                finding.external_domain
                for finding in evidence
                if finding.external_domain is not None
            )
        )
        categories[name] = BehaviorCategory(
            detected=bool(evidence), evidence=tuple(evidence), external_domains=domains
        )

    return BehaviorProfile(**categories)
