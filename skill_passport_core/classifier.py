"""Deterministic comparison of a Behavior Profile against repository claims."""

from __future__ import annotations

import re
from dataclasses import dataclass

from skill_passport_core.profile import BEHAVIOR_CATEGORIES, BehaviorProfile


@dataclass(frozen=True)
class Classification:
    category: str
    status: str
    claim_excerpt: str | None = None


_DENIAL_PATTERNS = {
    "network": (
        r"no\s+(?:outbound\s+)?network(?:\s+access)?(?:\s+required)?\.",
        r"never\s+(?:makes?|performs?)\s+(?:any\s+)?network\s+requests?",
        r"runs?\s+entirely\s+offline",
        r"does\s+not\s+transmit(?:\s+any)?\s+data",
    ),
    "filesystem": (
        r"no\s+file(?:system)?\s+access",
        r"never\s+(?:reads?|writes?)\s+(?:local\s+)?files?",
    ),
    "secrets": (
        r"does\s+not\s+(?:read|access)\s+(?:environment\s+)?(?:variables|secrets|credentials)",
        r"no\s+(?:api\s+)?keys?\s+or\s+credentials?",
    ),
    "shell": (
        r"no\s+(?:shell|subprocess|command)\s+(?:execution|access)",
        r"never\s+(?:runs?|executes?)\s+(?:shell\s+)?commands?",
    ),
}

_DISCLOSURE_PATTERNS = {
    "network": (r"telemetry", r"network", r"outbound", r"https?://", r"transmit"),
    "filesystem": (r"file", r"pdf", r"extract", r"create", r"form", r"read", r"write"),
    "secrets": (r"environment\s+variables?", r"api\s+keys?", r"credentials?", r"secrets?"),
    "shell": (r"shell", r"subprocess", r"command\s+execution", r"runs?\s+commands?"),
}


def classify_behavior(profile: BehaviorProfile, claims_text: str) -> list[Classification]:
    """Classify each detected behavior using only deterministic text matching.

    Denials take precedence because an explicit contradiction is more specific
    than a generic mention of the same behavior.
    """
    classifications: list[Classification] = []
    for category in BEHAVIOR_CATEGORIES:
        if not profile.category(category).detected:
            continue
        denial = _first_match(claims_text, _DENIAL_PATTERNS[category])
        if denial is not None:
            classifications.append(Classification(category, "CONTRADICTION", denial))
            continue
        disclosure = _first_match(claims_text, _DISCLOSURE_PATTERNS[category])
        if disclosure is not None:
            classifications.append(Classification(category, "DISCLOSED", disclosure))
            continue
        classifications.append(Classification(category, "UNDISCLOSED"))
    return classifications


def _first_match(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match is not None:
            return match.group(0)
    return None
