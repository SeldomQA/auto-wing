"""Unit tests for AiFixtureBase retry/re-plan loop and JSON retry helper."""
from unittest.mock import MagicMock

import pytest

from autowing.core.ai_fixture_base import AiFixtureBase
from autowing.core.cache import cache_manager


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Isolate the shared cache manager and fix the retry budget."""
    cache_manager._reset_instances()
    monkeypatch.setenv("AUTOWING_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("AUTOWING_MAX_RETRIES", "2")
    yield
    cache_manager._reset_instances()


CONTEXT = {"url": "https://example.com"}


class TestAiActionLoop:
    def test_first_attempt_success(self):
        f = AiFixtureBase()
        compute = MagicMock(side_effect=lambda error_hint="": {"selector": "#a", "action": "click"})
        execute = MagicMock()
        f._ai_action_loop("click it", CONTEXT, compute, execute)
        assert compute.call_count == 1
        assert execute.call_count == 1
        # Fresh instruction was cached by _get_cached_or_compute
        assert f.cache_manager.get_intelligent("click it", CONTEXT)["selector"] == "#a"

    def test_replan_after_failure_updates_cache(self):
        f = AiFixtureBase()
        instructions = iter([{"selector": "#old"}, {"selector": "#new"}])
        compute = MagicMock(side_effect=lambda error_hint="": next(instructions))
        execute = MagicMock(side_effect=[ValueError("locator timeout"), None])
        f._ai_action_loop("click it", CONTEXT, compute, execute)
        assert compute.call_count == 2
        # The second compute call carried the error as re-plan context
        assert compute.call_args_list[1][0][0] == "locator timeout"
        # The successful replanned instruction replaced the cached one
        assert f.cache_manager.get_intelligent("click it", CONTEXT)["selector"] == "#new"
        # Both executions ran with from_cache=False (fresh instructions)
        assert execute.call_args_list[1][0][1] is False

    def test_all_attempts_exhausted_raises_last_error(self):
        f = AiFixtureBase()
        compute = MagicMock(side_effect=lambda error_hint="": {"selector": "#a", "action": "click"})
        execute = MagicMock(side_effect=ValueError("still failing"))
        with pytest.raises(ValueError, match="still failing"):
            f._ai_action_loop("click it", CONTEXT, compute, execute)
        # 1 initial + 2 retries (AUTOWING_MAX_RETRIES=2)
        assert execute.call_count == 3
        assert compute.call_count == 3

    def test_cached_instruction_flagged_from_cache(self):
        f = AiFixtureBase()
        f.cache_manager.set_intelligent("click it", CONTEXT, {"selector": "#cached"})
        compute = MagicMock(side_effect=lambda error_hint="": {"selector": "#fresh"})
        execute = MagicMock()
        f._ai_action_loop("click it", CONTEXT, compute, execute)
        assert compute.call_count == 0
        instruction, from_cache = execute.call_args[0]
        assert instruction["selector"] == "#cached"
        assert from_cache is True
        # The _from_cache marker must not leak into the instruction
        assert "_from_cache" not in instruction

    def test_cached_failure_then_replan_success(self):
        f = AiFixtureBase()
        f.cache_manager.set_intelligent("click it", CONTEXT, {"selector": "#stale"})
        compute = MagicMock(side_effect=lambda error_hint="": {"selector": "#fresh"})
        execute = MagicMock(side_effect=[ValueError("cached selector stale"), None])
        f._ai_action_loop("click it", CONTEXT, compute, execute)
        # Cache entry evicted and replaced by the working instruction
        assert f.cache_manager.get_intelligent("click it", CONTEXT)["selector"] == "#fresh"


class TestLlmJsonRetry:
    def make_fixture(self, responses):
        f = AiFixtureBase()
        f.llm_client = MagicMock()
        f.llm_client.complete.side_effect = responses
        return f

    def test_valid_first_try(self):
        f = self.make_fixture(['{"selector": "#a", "action": "click"}'])
        result = f._llm_json_with_retry("prompt", lambda r: r)
        assert result["selector"] == "#a"
        assert f.llm_client.complete.call_count == 1

    def test_invalid_then_valid_with_error_feedback(self):
        f = self.make_fixture(["not json at all", '{"ok": 1}'])
        result = f._llm_json_with_retry("base prompt", lambda r: r)
        assert result == {"ok": 1}
        assert f.llm_client.complete.call_count == 2
        second_prompt = f.llm_client.complete.call_args_list[1][0][0]
        # Retry prompt carries the error and the previous bad response
        assert "could not be used" in second_prompt
        assert "not json at all" in second_prompt
        assert "base prompt" in second_prompt

    def test_validation_error_triggers_retry(self):
        def needs_selector(r):
            if "selector" not in r:
                raise ValueError("missing selector")
            return r

        f = self.make_fixture(['{"action": "click"}', '{"selector": "#a", "action": "click"}'])
        result = f._llm_json_with_retry("p", needs_selector)
        assert result["selector"] == "#a"
        assert f.llm_client.complete.call_count == 2

    def test_all_attempts_fail_raises_value_error(self):
        f = self.make_fixture(["bad", "still bad", "nope"])
        with pytest.raises(ValueError, match="invalid JSON"):
            f._llm_json_with_retry("p", lambda r: r)
        # 1 initial + 2 retries (AUTOWING_MAX_RETRIES=2)
        assert f.llm_client.complete.call_count == 3

    def test_markdown_wrapped_json_is_cleaned(self):
        f = self.make_fixture(['```json\n{"selector": "#a"}\n```'])
        result = f._llm_json_with_retry("p", lambda r: r)
        assert result == {"selector": "#a"}
