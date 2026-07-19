"""Fetch each fixture and print the claims and source paths discovered."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skill_passport_core.fetcher import FetchError, fetch_repository


FIXTURES = {
    "VERIFIED": "https://github.com/shaheerasim320/text-formatter",
    "REVIEW": "https://github.com/shaheerasim320/project-helper",
    "HIGH_RISK": "https://github.com/shaheerasim320/auto-formatter",
    "DISCLOSED_FILESYSTEM": "https://github.com/anthropics/skills/tree/main/skills/pdf/scripts",
}


def print_paths(label, paths):
    print(f"  {label}: {len(paths)}")
    for path in paths:
        print(f"    - {path}")


def main():
    for name, url in FIXTURES.items():
        print(f"{name}: {url}")
        try:
            result = fetch_repository(url)
        except FetchError as error:
            print(f"  ERROR: {error}")
            continue
        print(f"  ref: {result.ref}")
        print_paths("claims files", result.claims_paths)
        print_paths("source files", result.source_paths)


if __name__ == "__main__":
    main()
