"""Tests for iframe / Shadow DOM coverage of marker injection and element
collection scripts (plan item F5)."""
import importlib.util

import pytest

from autowing.core.ai_fixture_web import (
    build_clear_markers_script,
    build_elements_collection_script,
    build_marker_injection_script,
)

_SELENIUM_AVAILABLE = importlib.util.find_spec("selenium") is not None

# Main page: a top-level button, an open shadow root and a same-origin
# (srcdoc) iframe, each containing one button.
PAGE_HTML = """
<html>
<body>
  <button id="top-btn">Top Button</button>
  <div id="shadow-host"></div>
  <iframe id="child" srcdoc='<button id="frame-btn" onclick="window.__frameClicked=true">Frame Button</button>'></iframe>
  <script>
    // IIFE: set_content reuses the global environment across calls, so
    // top-level const declarations would collide on the second load.
    (() => {
      const host = document.getElementById('shadow-host');
      const root = host.attachShadow({mode: 'open'});
      const btn = document.createElement('button');
      btn.id = 'shadow-btn';
      btn.textContent = 'Shadow Button';
      root.appendChild(btn);
    })();
  </script>
</body>
</html>
"""


class TestSharedScripts:
    def test_all_scripts_traverse_iframes_and_shadow_roots(self):
        for script in (build_marker_injection_script(),
                       build_elements_collection_script(),
                       build_clear_markers_script()):
            assert "awWalkScopes" in script
            assert "contentDocument" in script
            assert "shadowRoot" in script
            # placeholders resolved, and the result is a single IIFE expression
            assert "__SCOPE_WALKER__" not in script
            assert script.startswith("(() => {")
            assert script.endswith("})();")

    def test_marker_script_marks_interactive_elements(self):
        script = build_marker_injection_script()
        assert "data-autowing-id" in script
        assert "'input:not([type=\"hidden\"])'" in script
        assert "inFrame: frameDepth > 0" in script

    def test_elements_script_keeps_visibility_filter_and_marker_link(self):
        script = build_elements_collection_script()
        assert "offsetWidth > 0" in script
        assert "autowingId: el.getAttribute('data-autowing-id')" in script
        assert "inFrame: frameDepth > 0" in script


# ---------------------------------------------------------------------------
# Real-browser coverage tests (skipped when chromium cannot be launched)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def browser_page():
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = None
    # Prefer the bundled chromium; fall back to a system-installed Chrome /
    # Edge channel when playwright browsers have not been downloaded.
    for launch_kwargs in ({}, {"channel": "chrome"}, {"channel": "msedge"}):
        try:
            browser = pw.chromium.launch(headless=True, **launch_kwargs)
            break
        except Exception:
            continue
    if browser is None:
        pw.stop()
        pytest.skip("no chromium / chrome / msedge browser available")
    page = browser.new_page()
    yield page
    page.close()
    browser.close()
    pw.stop()


def _make_fixture(page, cache_dir):
    """Build a PlaywrightAiFixture without touching LLMFactory/env config."""
    from unittest.mock import MagicMock

    from autowing.core.cache.cache_manager import IntelligentCacheManager
    from autowing.playwright.fixture import PlaywrightAiFixture

    f = PlaywrightAiFixture.__new__(PlaywrightAiFixture)
    f._vision_enabled = False
    f._max_action_retries = 1
    f._element_markers = {}
    f._inject_markers_enabled = True
    f.cache_manager = IntelligentCacheManager(cache_dir=cache_dir)
    f.llm_client = MagicMock()
    f.page = page
    return f


def _load_test_page(page):
    page.set_content(PAGE_HTML)
    page.wait_for_function(
        "(() => { const f = document.getElementById('child');"
        " const d = f && f.contentDocument;"
        " return d && d.readyState === 'complete' && d.getElementById('frame-btn'); })()"
    )


class TestCrossFrameCoverage:
    def test_markers_reach_iframe_and_shadow_dom(self, browser_page, tmp_path):
        page = browser_page
        _load_test_page(page)
        f = _make_fixture(page, str(tmp_path / "cache-markers"))

        f._inject_element_markers()
        markers = list(f._element_markers.values())
        texts = {m.get("textContent") for m in markers}
        assert {"Top Button", "Frame Button", "Shadow Button"} <= texts

        # the iframe element carries the nested-frame hint
        frame_marker = next(m for m in markers if m.get("textContent") == "Frame Button")
        assert frame_marker["inFrame"] is True

        # the attribute was really written into the iframe document
        attr = page.evaluate("document.getElementById('child').contentDocument"
                             ".getElementById('frame-btn').getAttribute('data-autowing-id')")
        assert attr and attr.startswith("aw-")
        # and into the open shadow root
        assert page.evaluate("document.getElementById('shadow-host').shadowRoot"
                             ".querySelector('button').hasAttribute('data-autowing-id')") is True

    def test_elements_collection_and_cross_frame_clear(self, browser_page, tmp_path):
        page = browser_page
        _load_test_page(page)
        f = _make_fixture(page, str(tmp_path / "cache-elements"))

        f._inject_element_markers()
        elements = f._execute_elements_script()
        ids = {e.get("id") for e in elements}
        assert {"top-btn", "frame-btn", "shadow-btn"} <= ids
        frame_el = next(e for e in elements if e.get("id") == "frame-btn")
        assert frame_el["inFrame"] is True
        assert frame_el["autowingId"]  # linked to the injected marker

        # clearing also removes markers inside the iframe document
        f._clear_element_markers()
        assert f._element_markers == {}
        attr = page.evaluate("document.getElementById('child').contentDocument"
                             ".getElementById('frame-btn').getAttribute('data-autowing-id')")
        assert attr is None


class TestAiActionFrameScope:
    def test_ai_action_scoped_to_frame_locator(self, browser_page, tmp_path):
        page = browser_page
        _load_test_page(page)
        f = _make_fixture(page, str(tmp_path / "cache-action"))
        f.llm_client.complete.return_value = '{"selector": "button#frame-btn", "action": "click"}'

        # positional frame argument, matching examples/test_playwright_iframes.py
        f.ai_action('点击 iframe 中的按钮', page.frame_locator("#child"))

        clicked = page.evaluate("document.getElementById('child').contentDocument"
                                ".defaultView.__frameClicked === true")
        assert clicked is True

    def test_resolve_frame_variants(self, browser_page, tmp_path):
        page = browser_page
        _load_test_page(page)
        f = _make_fixture(page, str(tmp_path / "cache-resolve"))

        assert f._resolve_frame(None) is None
        # FrameLocator / selector string both resolve to the same frame
        via_fl = f._resolve_frame(page.frame_locator("#child"))
        via_selector = f._resolve_frame("#child")
        assert via_fl is not None and via_selector is not None
        assert via_fl.url == via_selector.url
        with pytest.raises(TypeError):
            f._resolve_frame(123)


# ---------------------------------------------------------------------------
# Selenium cross-frame marker lookup (mocked driver, no browser needed)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SELENIUM_AVAILABLE, reason="selenium not installed")
class TestSeleniumFrameSearch:
    @staticmethod
    def _make_driver(tree):
        from autowing.selenium.fixture import SeleniumAiFixture

        class FakeSwitchTo:
            def __init__(self):
                self.stack = []

            def frame(self, frame):
                self.stack.append(frame)

            def parent_frame(self):
                self.stack.pop()

        class FakeDriver:
            def __init__(self, tree):
                self.tree = tree
                self.switch_to = FakeSwitchTo()

            def find_elements(self, by, value):
                scope = self.switch_to.stack[-1] if self.switch_to.stack else "root"
                node = self.tree.get(scope, {})
                if value in node.get("match", []):
                    return [f"ELEMENT@{scope}"]
                return node.get("frames", [])

        f = SeleniumAiFixture.__new__(SeleniumAiFixture)
        f.driver = FakeDriver(tree)
        return f

    def test_recurses_into_nested_frames_and_stays_switched(self):
        tree = {
            "root": {"frames": ["f1"]},
            "f1": {"frames": ["f2"]},
            "f2": {"match": ['[data-autowing-id="aw-x"]']},
        }
        f = self._make_driver(tree)
        found = f._find_in_frames("css selector", '[data-autowing-id="aw-x"]')
        assert found == "ELEMENT@f2"
        # driver remains switched into the containing frame
        assert f.driver.switch_to.stack == ["f1", "f2"]

    def test_restores_frame_state_when_not_found(self):
        tree = {
            "root": {"frames": ["f1"]},
            "f1": {"frames": ["f2"]},
            "f2": {},
        }
        f = self._make_driver(tree)
        assert f._find_in_frames("css selector", '[data-autowing-id="aw-missing"]') is None
        assert f.driver.switch_to.stack == []
