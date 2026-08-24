"""Unit tests for the debug aids (plan item F6).

Covers: failure screenshots, execution trace file, AUTOWING_DEBUG prompt /
response logging and the AUTOWING_ACTION_TIMEOUT / AUTOWING_SCREENSHOT_DIR
configuration. No browser or LLM needed.
"""
import base64
import json
from unittest.mock import MagicMock

import pytest

from autowing.core.ai_fixture_base import AiFixtureBase
from autowing.core.cache import cache_manager

# Smallest valid 1x1 PNG
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNg"
    "YGD4DwABBAEAgcAgfwAAAABJRU5ErkJggg=="
)
_PNG_B64 = base64.b64encode(_PNG_BYTES).decode("utf-8")


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Isolate the shared cache manager and put debug artefacts in tmp."""
    cache_manager._reset_instances()
    monkeypatch.setenv("AUTOWING_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("AUTOWING_MAX_RETRIES", "1")
    monkeypatch.delenv("AUTOWING_DEBUG", raising=False)
    monkeypatch.delenv("AUTOWING_ACTION_TIMEOUT", raising=False)
    monkeypatch.delenv("AUTOWING_SCREENSHOT_DIR", raising=False)
    yield tmp_path
    cache_manager._reset_instances()


class TestConfiguration:
    def test_defaults(self):
        f = AiFixtureBase()
        assert f._debug_enabled is False
        assert f._action_timeout == 30.0
        # Screenshots default next to the cache dir, trace file likewise
        assert f._screenshot_dir.endswith("screenshots")
        assert f._trace_path.endswith("trace.jsonl")

    def test_env_overrides(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AUTOWING_DEBUG", "true")
        monkeypatch.setenv("AUTOWING_ACTION_TIMEOUT", "7")
        monkeypatch.setenv("AUTOWING_SCREENSHOT_DIR", str(tmp_path / "shots"))
        f = AiFixtureBase()
        assert f._debug_enabled is True
        assert f._action_timeout == 7.0
        assert f._screenshot_dir == str(tmp_path / "shots")

    def test_invalid_timeout_falls_back(self, monkeypatch):
        monkeypatch.setenv("AUTOWING_ACTION_TIMEOUT", "not-a-number")
        assert AiFixtureBase()._action_timeout == 30.0


class TestFailureScreenshot:
    @staticmethod
    def _make_fixture(tmp_path, capture):
        f = AiFixtureBase.__new__(AiFixtureBase)
        f._screenshot_dir = str(tmp_path / "shots")
        f._capture_screenshot_base64 = capture
        return f

    def test_saves_png_and_returns_path(self, tmp_path):
        f = self._make_fixture(tmp_path, lambda: _PNG_B64)
        path = f._save_failure_screenshot("点击 提交 按钮!")
        assert path is not None
        with open(path, "rb") as fh:
            assert fh.read() == _PNG_BYTES
        name = path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
        assert name.startswith("ai_action_failure_")
        # Non-alnum chars are stripped from the prompt hint
        assert "提交按钮" in name

    def test_unavailable_capture_returns_none(self, tmp_path):
        f = self._make_fixture(tmp_path, lambda: None)
        assert f._save_failure_screenshot("x") is None

    def test_capture_error_is_swallowed(self, tmp_path):
        def boom():
            raise RuntimeError("browser closed")

        f = self._make_fixture(tmp_path, boom)
        assert f._save_failure_screenshot("x") is None


class TestExecutionTrace:
    def test_appends_jsonl_lines(self, tmp_path):
        f = AiFixtureBase.__new__(AiFixtureBase)
        f._trace_path = str(tmp_path / "trace.jsonl")
        f._record_trace("ai_action_success", "click it", attempt=1,
                        instruction={"selector": "#a"})
        f._record_trace("ai_action_attempt_failed", "click it", attempt=2,
                        error=ValueError("boom"), screenshot=None)
        lines = [json.loads(line) for line in
                 (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
        assert [line["event"] for line in lines] == [
            "ai_action_success", "ai_action_attempt_failed"]
        assert lines[0]["prompt"] == "click it"
        assert lines[0]["instruction"] == {"selector": "#a"}
        # Exceptions are serialized as strings, never raised
        assert lines[1]["error"] == "boom"
        for line in lines:
            assert "time" in line

    def test_missing_trace_path_is_noop(self):
        f = AiFixtureBase.__new__(AiFixtureBase)  # no _trace_path attribute
        f._record_trace("whatever", "prompt")  # must not raise


class TestDebugLogging:
    def test_full_prompt_and_response_logged(self, monkeypatch):
        import autowing.core.ai_fixture_base as base_mod

        fake_logger = MagicMock()
        monkeypatch.setattr(base_mod, "logger", fake_logger)

        f = AiFixtureBase()
        f._debug_enabled = True
        f.llm_client = MagicMock()
        f.llm_client.complete.return_value = "raw-llm-answer"

        assert f._llm_complete("my secret prompt") == "raw-llm-answer"
        infos = [call.args[0] for call in fake_logger.info.call_args_list]
        assert any("AUTOWING_DEBUG" in msg and "my secret prompt" in msg
                   for msg in infos)
        assert any("raw-llm-answer" in msg for msg in infos)

    def test_debug_off_keeps_llm_io_private(self, monkeypatch):
        import autowing.core.ai_fixture_base as base_mod

        fake_logger = MagicMock()
        monkeypatch.setattr(base_mod, "logger", fake_logger)

        f = AiFixtureBase()
        f._debug_enabled = False
        f.llm_client = MagicMock()
        f.llm_client.complete.return_value = "raw-llm-answer"

        f._llm_complete("my secret prompt")
        infos = " ".join(call.args[0] for call in fake_logger.info.call_args_list)
        assert "my secret prompt" not in infos
        assert "raw-llm-answer" not in infos


class TestLoopDebugIntegration:
    """_ai_action_loop must screenshot every failed attempt and trace the run."""

    def test_failure_triggers_screenshot_and_trace(self, tmp_path):
        f = AiFixtureBase()
        captured = MagicMock()
        f._save_failure_screenshot = captured

        compute = MagicMock(side_effect=lambda error_hint="": {"selector": "#a", "action": "click"})
        execute = MagicMock(side_effect=ValueError("locator gone"))
        with pytest.raises(ValueError, match="locator gone"):
            f._ai_action_loop("click it", {"url": "https://e.com"}, compute, execute)

        # One screenshot per failed attempt (1 initial + 1 retry)
        assert captured.call_count == 2
        events = [json.loads(line)["event"] for line in
                  (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
        assert events == ["ai_action_attempt_failed", "ai_action_attempt_failed",
                          "ai_action_failed"]

    def test_success_is_traced(self, tmp_path):
        f = AiFixtureBase()
        compute = MagicMock(side_effect=lambda error_hint="": {"selector": "#a", "action": "click"})
        f._ai_action_loop("click it", {"url": "https://e.com"}, compute, MagicMock())

        lines = [json.loads(line) for line in
                 (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
        assert len(lines) == 1
        assert lines[0]["event"] == "ai_action_success"
        assert lines[0]["instruction"]["selector"] == "#a"
