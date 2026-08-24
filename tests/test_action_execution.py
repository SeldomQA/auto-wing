"""Unit tests for the extended ai_action action set (plan item F2).

Execution dispatch is verified with mocked drivers - no browser needed.
"""
import importlib.util
from unittest.mock import MagicMock

import pytest

from autowing.core.cache.cache_manager import IntelligentCacheManager
from autowing.playwright.fixture import PlaywrightAiFixture

_SELENIUM_AVAILABLE = importlib.util.find_spec("selenium") is not None


def _make_playwright_fixture():
    f = PlaywrightAiFixture.__new__(PlaywrightAiFixture)
    f._vision_enabled = False
    f._max_action_retries = 0
    f._action_timeout = 30
    f._element_markers = {}
    f._inject_markers_enabled = False
    f.cache_manager = MagicMock(spec=IntelligentCacheManager)
    f.llm_client = MagicMock()
    f.page = MagicMock()
    return f


class TestPlaywrightActionDispatch:
    def test_click(self):
        f = _make_playwright_fixture()
        f._execute_action_instruction({"selector": "#btn", "action": "click"})
        f.page.locator.return_value.click.assert_called_once()

    def test_fill_with_key(self):
        f = _make_playwright_fixture()
        f._execute_action_instruction(
            {"selector": "#q", "action": "fill", "value": "hello", "key": "Enter"})
        element = f.page.locator.return_value
        element.fill.assert_called_once_with("hello", timeout=30000)
        element.press.assert_called_once_with("Enter", timeout=30000)

    def test_select_by_value(self):
        f = _make_playwright_fixture()
        f._execute_action_instruction(
            {"selector": "#city", "action": "select", "value": "bj"})
        f.page.locator.return_value.select_option.assert_called_once_with(
            value="bj", timeout=30000)

    def test_select_falls_back_to_label(self):
        f = _make_playwright_fixture()
        element = f.page.locator.return_value
        element.select_option.side_effect = [Exception("no option with value"), None]
        f._execute_action_instruction(
            {"selector": "#city", "action": "select", "value": "北京"})
        assert element.select_option.call_args_list[-1].kwargs == {"label": "北京", "timeout": 30000}

    def test_select_requires_value(self):
        f = _make_playwright_fixture()
        with pytest.raises(ValueError, match="requires 'value'"):
            f._execute_action_instruction({"selector": "#city", "action": "select"})

    def test_hover(self):
        f = _make_playwright_fixture()
        f._execute_action_instruction({"selector": "#menu", "action": "hover"})
        f.page.locator.return_value.hover.assert_called_once()

    def test_check_and_uncheck(self):
        f = _make_playwright_fixture()
        f._execute_action_instruction({"selector": "#agree", "action": "check"})
        f.page.locator.return_value.check.assert_called_once()
        f._execute_action_instruction({"selector": "#agree", "action": "uncheck"})
        f.page.locator.return_value.uncheck.assert_called_once()

    def test_scroll_into_view(self):
        f = _make_playwright_fixture()
        f._execute_action_instruction({"selector": "#footer", "action": "scroll"})
        f.page.locator.return_value.scroll_into_view_if_needed.assert_called_once()

    def test_upload(self):
        f = _make_playwright_fixture()
        f._execute_action_instruction(
            {"selector": "#file", "action": "upload", "value": "a.png"})
        f.page.locator.return_value.set_input_files.assert_called_once_with(
            "a.png", timeout=30000)

    def test_upload_requires_value(self):
        f = _make_playwright_fixture()
        with pytest.raises(ValueError, match="requires 'value'"):
            f._execute_action_instruction({"selector": "#file", "action": "upload"})

    def test_unknown_action_raises(self):
        f = _make_playwright_fixture()
        with pytest.raises(ValueError, match="Unsupported action"):
            f._execute_action_instruction({"selector": "#x", "action": "dance"})

    def test_missing_selector_or_action_raises(self):
        f = _make_playwright_fixture()
        with pytest.raises(ValueError, match="Invalid instruction"):
            f._execute_action_instruction({"action": "click"})
        with pytest.raises(ValueError, match="Invalid instruction"):
            f._execute_action_instruction({"selector": "#x"})


@pytest.mark.skipif(not _SELENIUM_AVAILABLE, reason="selenium not installed")
class TestSeleniumActionDispatch:
    @staticmethod
    def _make_fixture():
        from autowing.selenium.fixture import SeleniumAiFixture

        f = SeleniumAiFixture.__new__(SeleniumAiFixture)
        f._vision_enabled = False
        f._max_action_retries = 0
        f._element_markers = {}
        f._inject_markers_enabled = False
        f.cache_manager = MagicMock(spec=IntelligentCacheManager)
        f.llm_client = MagicMock()
        f.driver = MagicMock()
        f.wait = MagicMock()
        return f

    def test_select_by_value_with_visible_text_fallback(self, monkeypatch):
        import autowing.selenium.fixture as sel_mod

        select_mock = MagicMock()
        select_mock.select_by_value.side_effect = [Exception("no such value"), None]
        monkeypatch.setattr(sel_mod, "Select", MagicMock(return_value=select_mock))

        f = self._make_fixture()
        element = f.wait.until.return_value
        # fallback path: value fails once, then visible text is used
        f._execute_action_instruction(
            {"selector": "//select", "action": "select", "value": "北京"})
        select_mock.select_by_visible_text.assert_called_once_with("北京")
        assert element is not None

    def test_hover_uses_action_chains(self, monkeypatch):
        import autowing.selenium.fixture as sel_mod

        chains = MagicMock()
        monkeypatch.setattr(sel_mod, "ActionChains", MagicMock(return_value=chains))
        f = self._make_fixture()
        f._execute_action_instruction({"selector": "//div", "action": "hover"})
        chains.move_to_element.assert_called_once_with(f.wait.until.return_value)
        chains.perform.assert_called_once()

    def test_check_clicks_only_when_state_differs(self):
        f = self._make_fixture()
        element = f.wait.until.return_value
        element.is_selected.return_value = False
        f._execute_action_instruction({"selector": "//input", "action": "check"})
        element.click.assert_called_once()
        # already checked -> no extra click
        element.click.reset_mock()
        element.is_selected.return_value = True
        f._execute_action_instruction({"selector": "//input", "action": "check"})
        element.click.assert_not_called()

    def test_scroll_uses_javascript(self):
        f = self._make_fixture()
        f._execute_action_instruction({"selector": "//div", "action": "scroll"})
        args = f.driver.execute_script.call_args[0]
        assert "scrollIntoView" in args[0]
        assert args[1] is f.wait.until.return_value

    def test_upload_sends_file_path(self):
        f = self._make_fixture()
        f._execute_action_instruction(
            {"selector": "//input", "action": "upload", "value": "a.png"})
        f.wait.until.return_value.send_keys.assert_called_once_with("a.png")

    def test_unknown_action_raises(self):
        f = self._make_fixture()
        with pytest.raises(ValueError, match="Unsupported action"):
            f._execute_action_instruction({"selector": "//x", "action": "dance"})
