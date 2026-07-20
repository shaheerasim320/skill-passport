from pathlib import Path

import cli


ROOT = Path(__file__).resolve().parents[1]


def test_missing_codex_shows_clear_error_after_deterministic_stages(monkeypatch, capsys):
    def missing_codex(*args, **kwargs):
        raise FileNotFoundError("codex")

    monkeypatch.setattr("skill_passport_core.reasoner.subprocess.run", missing_codex)

    exit_code = cli.main(["check", str(ROOT / "fixtures" / "high_risk")])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Repository Behavior" in captured.out
    assert "Comparing repository claims..." in captured.out
    assert "No network access required." in captured.out
    assert "Codex CLI not found. Install it with: npm install -g @openai/codex" in captured.err
    assert "Traceback" not in captured.err
