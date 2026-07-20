from skill_passport_core.fetcher import RepositoryNotFoundError
from skill_passport_core.reasoner import ReasonerError, Verdict
from web.backend.main import FollowUpRequest, _analysis_stream, follow_up


PROFILE = {
    "network": {"detected": False, "evidence": [], "external_domains": []},
    "filesystem": {"detected": False, "evidence": []},
    "secrets": {"detected": False, "evidence": []},
    "shell": {"detected": False, "evidence": []},
}


def _emit_stages(callback):
    callback("fetching", {"target": "https://github.com/example/clean"})
    callback("parsing", {"claims_files": ["SKILL.md"], "source_files": ["formatter.py"]})
    callback("tracing", {"source_file_count": 1, "findings": []})
    callback("profiling", {"finding_count": 0, "behavior_profile": PROFILE})
    callback("classifying", {"classifications": []})
    callback("reasoning", {})


def test_analysis_streams_profile_before_final_verdict(monkeypatch):
    def fake_analysis(github_url, stage_callback):
        _emit_stages(stage_callback)
        return Verdict(
            trust_level="verified",
            behavior_profile=PROFILE,
            evidence=[],
            classifications=[],
            reasoning={"judgment": "Clean.", "translation": "No findings."},
            recommendation="Review before installing.",
            install_command="npx skills add example/clean",
            thread_id="thread-1",
        )

    monkeypatch.setattr("web.backend.main.analyze_repository", fake_analysis)

    response = "".join(_analysis_stream("https://github.com/example/clean"))

    assert response.index("event: profile") < response.index("event: verdict")
    assert '"stage": "reasoning"' in response
    assert '"trust_level": "verified"' in response


def test_analysis_streams_error_after_progress(monkeypatch):
    def failed_analysis(github_url, stage_callback):
        _emit_stages(stage_callback)
        raise ReasonerError("Codex CLI not found.")

    monkeypatch.setattr("web.backend.main.analyze_repository", failed_analysis)

    response = "".join(_analysis_stream("https://github.com/example/clean"))

    assert response.index("event: profile") < response.index("event: error")
    assert '"code": "reasoning_unavailable"' in response
    assert '"message": "Codex CLI not found."' in response


def test_follow_up_reuses_the_returned_thread(monkeypatch):
    received = {}

    def fake_follow_up(question, thread_id):
        received.update(question=question, thread_id=thread_id)
        return "The domain is not justified by the repository claim."

    monkeypatch.setattr("web.backend.main.answer_follow_up", fake_follow_up)

    response = follow_up(
        FollowUpRequest(thread_id="thread-1", question="Could this be legitimate telemetry?")
    )

    assert response == {"answer": "The domain is not justified by the repository claim."}
    assert received == {
        "thread_id": "thread-1",
        "question": "Could this be legitimate telemetry?",
    }


def test_analysis_streams_a_safe_repository_not_found_error(monkeypatch):
    def missing_repository(github_url, stage_callback):
        raise RepositoryNotFoundError("GitHub API returned HTTP 404: raw payload")

    monkeypatch.setattr("web.backend.main.analyze_repository", missing_repository)

    response = "".join(_analysis_stream("https://github.com/example/missing"))

    assert '"code": "repository_not_found"' in response
    assert "Repository not found or not publicly accessible." in response
    assert "raw payload" not in response
