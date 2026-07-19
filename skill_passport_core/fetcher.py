"""Read-only GitHub REST API repository fetching.

This module never clones, installs, imports, or executes fetched repository
content.  It only retrieves text files and preserves their repository paths.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


GITHUB_API = "https://api.github.com"
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
CLAIMS_FILENAMES = {"skill.md", "package.json", "manifest.json", "mcp.json"}


class FetchError(RuntimeError):
    """Raised when a public GitHub repository cannot be fetched."""


@dataclass(frozen=True)
class RepositoryTarget:
    owner: str
    repository: str
    ref: str | None = None
    path: str = ""


@dataclass(frozen=True)
class FetchedFile:
    path: str
    content: str


@dataclass(frozen=True)
class RepositoryFetchResult:
    github_url: str
    owner: str
    repository: str
    ref: str
    source_root: str
    claims_files: tuple[FetchedFile, ...]
    source_files: tuple[FetchedFile, ...]

    @property
    def claims_paths(self) -> tuple[str, ...]:
        return tuple(file.path for file in self.claims_files)

    @property
    def source_paths(self) -> tuple[str, ...]:
        return tuple(file.path for file in self.source_files)


def parse_github_url(github_url: str) -> RepositoryTarget:
    """Parse a public github.com repository URL, optionally with a tree path."""
    normalized = github_url.strip()
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"

    parsed = urlparse(normalized)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("GitHub URL must use github.com")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub URL must include owner and repository")

    owner, repository = parts[0], parts[1]
    if len(parts) == 2:
        return RepositoryTarget(owner=owner, repository=repository.removesuffix(".git"))
    if len(parts) < 4 or parts[2] != "tree":
        raise ValueError("Use a repository URL or a /tree/<ref>/<path> URL")

    return RepositoryTarget(
        owner=owner,
        repository=repository.removesuffix(".git"),
        ref=parts[3],
        path="/".join(parts[4:]),
    )


class GitHubRepositoryFetcher:
    """Fetch claims and source text from a public GitHub repository via REST."""

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch(self, github_url: str) -> RepositoryFetchResult:
        target = parse_github_url(github_url)
        metadata = self._get_json(f"/repos/{target.owner}/{target.repository}")
        ref = target.ref or metadata["default_branch"]
        tree = self._get_json(
            f"/repos/{target.owner}/{target.repository}/git/trees/{ref}?recursive=1"
        )
        if tree.get("truncated"):
            raise FetchError("GitHub tree response was truncated; narrow the repository URL to a subtree")

        blobs = [entry for entry in tree["tree"] if entry["type"] == "blob"]
        source_root = target.path.strip("/")
        claim_paths = sorted(
            entry["path"]
            for entry in blobs
            if self._is_claims_file(entry["path"], source_root)
        )
        source_paths = sorted(
            entry["path"]
            for entry in blobs
            if self._is_source_file(entry["path"], source_root)
        )

        return RepositoryFetchResult(
            github_url=github_url,
            owner=target.owner,
            repository=target.repository,
            ref=ref,
            source_root=source_root,
            claims_files=tuple(self._fetch_file(target, ref, path) for path in claim_paths),
            source_files=tuple(self._fetch_file(target, ref, path) for path in source_paths),
        )

    def _get_json(self, path: str) -> dict[str, Any]:
        request = Request(
            f"{GITHUB_API}{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "skill-passport-fetcher",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise FetchError(f"GitHub API returned HTTP {error.code}: {detail}") from error
        except URLError as error:
            raise FetchError(f"Could not reach the GitHub API: {error.reason}") from error

    def _fetch_file(self, target: RepositoryTarget, ref: str, path: str) -> FetchedFile:
        data = self._get_json(
            f"/repos/{target.owner}/{target.repository}/contents/{path}?ref={ref}"
        )
        if data.get("encoding") != "base64":
            raise FetchError(f"GitHub did not return base64 content for {path}")
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return FetchedFile(path=path, content=content)

    @staticmethod
    def _is_source_file(path: str, source_root: str) -> bool:
        return (not source_root or path.startswith(f"{source_root}/")) and (
            PurePosixPath(path).suffix.lower() in SOURCE_SUFFIXES
        )

    @staticmethod
    def _is_claims_file(path: str, source_root: str) -> bool:
        filename = PurePosixPath(path).name.lower()
        is_claim = (
            filename.startswith("readme")
            or filename in CLAIMS_FILENAMES
            or "permission" in filename
        )
        if not is_claim:
            return False
        if not source_root:
            return True
        claim_path = PurePosixPath(path)
        root_path = PurePosixPath(source_root)
        return claim_path.is_relative_to(root_path) or root_path.is_relative_to(claim_path.parent)


def fetch_repository(github_url: str) -> RepositoryFetchResult:
    """Convenience function for fetching a public GitHub repository."""
    return GitHubRepositoryFetcher().fetch(github_url)
