"""Authentication remains optional for GitHub REST fetching."""

import json
from pathlib import Path

from skill_passport_core.fetcher import GitHubRepositoryFetcher


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"ok": True}).encode("utf-8")


def test_fetcher_uses_bearer_token_when_present(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        return FakeResponse()

    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr("skill_passport_core.fetcher.urlopen", fake_urlopen)

    assert GitHubRepositoryFetcher()._get_json("/rate_limit") == {"ok": True}
    assert captured["authorization"] == "Bearer test-token"


def test_fetcher_omits_authorization_when_token_is_missing(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        return FakeResponse()

    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setattr("skill_passport_core.fetcher.urlopen", fake_urlopen)

    assert GitHubRepositoryFetcher()._get_json("/rate_limit") == {"ok": True}
    assert captured["authorization"] is None


def test_fetcher_loads_current_directory_dotenv_for_pipx_users(monkeypatch, tmp_path):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        return FakeResponse()

    (Path(tmp_path) / ".env").write_text("GITHUB_TOKEN=cwd-token\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("SKILL_PASSPORT_ENV_FILE", raising=False)
    monkeypatch.setattr("skill_passport_core.fetcher.urlopen", fake_urlopen)

    assert GitHubRepositoryFetcher()._get_json("/rate_limit") == {"ok": True}
    assert captured["authorization"] == "Bearer cwd-token"
