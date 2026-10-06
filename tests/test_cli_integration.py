from __future__ import annotations

from typer.testing import CliRunner

from fake_like_detector.cli import app


def test_demo_and_analyze_end_to_end(tmp_path, monkeypatch) -> None:
    database = tmp_path / "demo.db"
    monkeypatch.setenv("FLED_DATABASE_URL", f"sqlite:///{database.as_posix()}")
    monkeypatch.setenv("FLED_PROVIDER", "mock")
    runner = CliRunner()
    demo = runner.invoke(app, ["demo"])
    assert demo.exit_code == 0, demo.output
    assert "highly_suspicious" in demo.output or "suspicious" in demo.output
    result = runner.invoke(app, ["analyze"])
    assert result.exit_code == 0, result.output
    assert "fake-account percentage" in result.output
