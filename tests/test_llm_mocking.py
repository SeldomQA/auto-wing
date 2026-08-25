"""Offline LLM mocking infrastructure tests (plan item T4).

Covers: the FakeLLMClient test double, factory-level mock registration,
constructor injection into all three driver fixtures, and end-to-end
ai_query / action-loop flows driven entirely by scripted responses.
No API key, no network, no browser needed.
"""
import json
from unittest.mock import MagicMock

import pytest

from autowing.core.ai_fixture_base import AiFixtureBase
from autowing.core.cache import cache_manager
from autowing.core.llm.base import BaseLLMClient
from autowing.core.llm.factory import LLMFactory

from tests.helpers import FakeLLMClient


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Isolate the shared cache manager and put cache artefacts in tmp."""
    cache_manager._reset_instances()
    monkeypatch.setenv("AUTOWING_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("AUTOWING_MAX_RETRIES", "1")
    yield tmp_path
    cache_manager._reset_instances()


class TestFakeLLMClient:
    def test_implements_interface(self):
        assert isinstance(FakeLLMClient(), BaseLLMClient)

    def test_scripted_responses_in_fifo_order(self):
        fake = FakeLLMClient(["first", "second"])
        assert fake.complete("p1") == "first"
        assert fake.complete("p2") == "second"
        assert fake.prompts == ["p1", "p2"]

    def test_last_response_repeated_when_exhausted(self):
        fake = FakeLLMClient(["only"])
        assert fake.complete("a") == "only"
        assert fake.complete("b") == "only"

    def test_unexpected_extra_call_raises(self):
        fake = FakeLLMClient([])
        with pytest.raises(AssertionError):
            fake.complete("surprise")

    def test_vision_payload_recorded(self):
        fake = FakeLLMClient(["vision-answer"])
        payload = [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]
        assert fake.complete_with_vision(payload) == "vision-answer"
        assert fake.vision_payloads == [payload]


class TestFactoryMockRegistration:
    def test_register_and_create_via_env(self, monkeypatch):
        monkeypatch.setitem(LLMFactory._models, "fake", FakeLLMClient)
        monkeypatch.setenv("AUTOWING_MODEL_PROVIDER", "fake")
        client = LLMFactory.create()
        assert isinstance(client, FakeLLMClient)

    def test_provider_lookup_is_case_insensitive(self, monkeypatch):
        monkeypatch.setitem(LLMFactory._models, "fake", FakeLLMClient)
        monkeypatch.setenv("AUTOWING_MODEL_PROVIDER", "FAKE")
        assert isinstance(LLMFactory.create(), FakeLLMClient)

    def test_unsupported_provider_raises(self, monkeypatch):
        monkeypatch.setenv("AUTOWING_MODEL_PROVIDER", "does-not-exist")
        with pytest.raises(ValueError, match="Unsupported model provider"):
            LLMFactory.create()


class TestConstructorInjection:
    def test_playwright_fixture_accepts_injected_client(self):
        from autowing.playwright.fixture import PlaywrightAiFixture

        fake = FakeLLMClient(["{}"])
        f = PlaywrightAiFixture(page=MagicMock(), llm_client=fake)
        assert f.llm_client is fake

    def test_selenium_fixture_accepts_injected_client(self):
        pytest.importorskip("selenium")
        from autowing.selenium.fixture import SeleniumAiFixture

        fake = FakeLLMClient(["{}"])
        f = SeleniumAiFixture(driver=MagicMock(), llm_client=fake)
        assert f.llm_client is fake

    def test_appium_fixture_accepts_injected_client(self):
        pytest.importorskip("appium")
        from autowing.appium.fixture import AppiumAiFixture

        fake = FakeLLMClient(["{}"])
        f = AppiumAiFixture(driver=MagicMock(), llm_client=fake)
        assert f.llm_client is fake


class TestOfflineAiQuery:
    """ai_query driven end-to-end by scripted LLM responses only."""

    @staticmethod
    def _make_fixture(fake: FakeLLMClient) -> AiFixtureBase:
        f = AiFixtureBase()  # real __init__: cache dir isolated by fixture
        f.llm_client = fake
        f._get_page_context = lambda: {
            "url": "https://example.com",
            "title": "Example",
            "elements": [{"text": "Welcome"}, {"text": "Sign in"}],
        }
        return f

    def test_json_response_parsed(self):
        fake = FakeLLMClient(['["Welcome", "Sign in"]'])
        f = self._make_fixture(fake)
        result = f.ai_query("string[]: page titles")
        assert result == ["Welcome", "Sign in"]
        assert len(fake.prompts) == 1
        # The built prompt must carry the page context to the model
        assert "Example" in fake.prompts[0]

    def test_fenced_json_response_cleaned(self):
        fake = FakeLLMClient(['```json\n{"answer": 42}\n```'])
        f = self._make_fixture(fake)
        assert f.ai_query("what is the answer") == {"answer": 42}

    def test_unparseable_response_raises_value_error(self):
        fake = FakeLLMClient(["totally not structured at all"])
        f = self._make_fixture(fake)
        with pytest.raises(ValueError):
            f.ai_query("string[]: list the titles")

    def test_vision_path_uses_scripted_response(self):
        fake = FakeLLMClient(['"blue"'])
        f = self._make_fixture(fake)
        f.enable_vision()
        f._capture_screenshot_base64 = lambda: "iVBOR-fake-base64"
        assert f.ai_query("what color is the button") == "blue"
        assert len(fake.vision_payloads) == 1
        assert not fake.prompts or fake.prompts[-1] == "<<vision>>"


class TestOfflineActionLoop:
    """_llm_json_with_retry / _ai_action_loop driven by scripted responses."""

    @staticmethod
    def _make_fixture(fake: FakeLLMClient) -> AiFixtureBase:
        f = AiFixtureBase.__new__(AiFixtureBase)
        f.cache_manager = MagicMock()
        f.cache_manager.get_intelligent.return_value = None  # never cached
        f.llm_client = fake
        f._vision_enabled = False
        f._max_action_retries = 1
        f._debug_enabled = False
        f._screenshot_dir = None
        f._trace_path = None
        return f

    def test_json_retry_feeds_error_back_into_prompt(self):
        fake = FakeLLMClient([
            "not json at all",
            '{"action": "click", "selector": "#submit"}',
        ])
        f = self._make_fixture(fake)
        result = f._llm_json_with_retry("find the button", lambda v: v)
        assert result == {"action": "click", "selector": "#submit"}
        assert len(fake.prompts) == 2
        assert "could not be used" in fake.prompts[1]

    def test_action_loop_replans_on_execution_failure(self):
        fake = FakeLLMClient([
            '{"action": "click", "selector": "#stale"}',
            '{"action": "click", "selector": "#retry"}',
        ])
        f = self._make_fixture(fake)
        executions = []

        def compute_action(error_hint: str = "") -> dict:
            prompt = "plan the click"
            if error_hint:
                prompt += f"\nprevious attempt failed: {error_hint}"
            return json.loads(f._llm_complete(prompt))

        def execute(instruction, from_cache=False):
            executions.append(instruction)
            if instruction["selector"] == "#stale":
                raise TimeoutError("element detached")

        f._ai_action_loop(
            "click the submit button",
            {"url": "https://example.com"},
            compute_action=compute_action,
            execute_action=execute,
        )
        assert [i["selector"] for i in executions] == ["#stale", "#retry"]
        # Re-plan prompt must carry the execution error
        assert "element detached" in fake.prompts[-1]
        # The stale cache entry is evicted and the re-plan is stored back
        f.cache_manager.invalidate.assert_called_once()
        assert f.cache_manager.set_intelligent.call_count == 2

    def test_action_loop_exhausts_retries_and_raises(self):
        fake = FakeLLMClient(['{"action": "click", "selector": "#broken"}'])
        f = self._make_fixture(fake)

        def execute(instruction, from_cache=False):
            raise TimeoutError("never works")

        with pytest.raises(TimeoutError, match="never works"):
            f._ai_action_loop(
                "click the ghost button",
                {"url": "https://example.com"},
                compute_action=lambda error_hint="": json.loads(
                    f._llm_complete("plan the click")),
                execute_action=execute,
            )
        # Initial compute + one re-plan, both scripted to the same response
        assert len(fake.prompts) == 2

    def test_cached_instruction_used_without_llm_call(self):
        fake = FakeLLMClient([])  # any LLM call would raise
        f = self._make_fixture(fake)
        f.cache_manager.get_intelligent.return_value = {
            "action": "click", "selector": "#cached"}
        executions = []

        f._ai_action_loop(
            "click the submit button",
            {"url": "https://example.com"},
            compute_action=lambda error_hint="": {},
            execute_action=lambda i, from_cache=False: executions.append(i),
        )
        assert executions == [{"action": "click", "selector": "#cached"}]
        assert fake.prompts == []
