"""Codex thread capture and resume behavior remain independent of fetching."""

import subprocess

from skill_passport_core.reasoner import _extract_answer_text, _invoke_codex, answer_follow_up


def test_initial_response_captures_thread_id(monkeypatch):
    stdout = "\n".join(
        (
            '{"type":"thread.started","thread_id":"thread-high-risk"}',
            '{"type":"item.completed","item":{"text":"{\\"trust_level\\": \\"high_risk\\"}"}}',
        )
    )

    monkeypatch.setattr(
        "skill_passport_core.reasoner.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout=stdout, stderr=""),
    )

    response = _invoke_codex("prompt", 30.0)

    assert response.thread_id == "thread-high-risk"
    assert response.output == {"trust_level": "high_risk"}


def test_follow_up_resumes_existing_thread_without_fetching(monkeypatch):
    captured = {}
    stdout = '{"type":"item.completed","item":{"text":"The API key is sent to telemetry.auto-formatter.dev."}}'

    def fake_run(command, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr("skill_passport_core.reasoner.subprocess.run", fake_run)

    answer = answer_follow_up("Could this be legitimate telemetry?", "thread-high-risk")

    assert answer == "The API key is sent to telemetry.auto-formatter.dev."
    assert captured["command"] == [
        "codex",
        "exec",
        "resume",
        "thread-high-risk",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        "Could this be legitimate telemetry?",
    ]


def test_follow_up_extracts_a_structured_answer_payload():
    """A resumed Codex thread may preserve a structured response format."""
    stdout = '{"type":"item.completed","item":{"text":"{\\"answer\\": \\"The API key reaches telemetry.example.dev.\\"}"}}'

    assert _extract_answer_text(stdout) == "The API key reaches telemetry.example.dev."


def test_codex_subprocess_uses_utf8_decoding(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    monkeypatch.setattr("skill_passport_core.reasoner.subprocess.run", fake_run)

    _invoke_codex("prompt", 30.0)

    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
