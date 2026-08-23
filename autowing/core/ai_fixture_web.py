"""
Common base class for web automation fixtures that provides shared functionality
for both Playwright and Selenium implementations.
"""
from typing import Any, Dict
from abc import ABC, abstractmethod

from loguru import logger
from autowing.core.ai_fixture_base import AiFixtureBase


# ---------------------------------------------------------------------------
# Shared browser-side scripts
#
# Playwright and Selenium run the exact same traversal logic so that marker
# injection, element collection and marker cleanup cover same-origin iframes
# and open shadow roots identically on both drivers. Cross-origin frames are
# skipped silently (their contentDocument is not accessible).
# ---------------------------------------------------------------------------

_INTERACTIVE_SELECTORS_JS = """[
                'input:not([type="hidden"])',
                'textarea',
                'select',
                'button',
                'a[href]',
                '[role="button"]',
                '[role="link"]',
                '[role="checkbox"]',
                '[role="radio"]',
                '[role="searchbox"]',
                'summary',
                '[contenteditable="true"]',
                '[tabindex]:not([tabindex="-1"])'
            ]"""

_ELEMENT_SELECTORS_JS = """[
                    'input',
                    'textarea',
                    'select',
                    'button',
                    'a',
                    '[role="button"]',
                    '[role="link"]',
                    '[role="checkbox"]',
                    '[role="radio"]',
                    '[role="searchbox"]',
                    'summary',
                    '[draggable="true"]'
                ]"""

# Recursive scope walker: visits a document/shadow root, then descends into
# every open shadow root and same-origin iframe/frame document (depth capped).
_SCOPE_WALKER_JS = """
            function awWalkScopes(scope, frameDepth, handler) {
                handler(scope, frameDepth);
                scope.querySelectorAll('*').forEach(function (el) {
                    if (el.shadowRoot) {
                        awWalkScopes(el.shadowRoot, frameDepth, handler);
                    }
                    if ((el.tagName === 'IFRAME' || el.tagName === 'FRAME') && frameDepth < 5) {
                        var frameDoc = null;
                        try { frameDoc = el.contentDocument; } catch (e) { frameDoc = null; }
                        if (frameDoc) {
                            awWalkScopes(frameDoc, frameDepth + 1, handler);
                        }
                    }
                });
            }
"""

_MARKER_SCRIPT_TEMPLATE = """
(() => {
    function generateUniqueId() {
        return 'aw-' + Math.random().toString(36).substr(2, 9);
    }

    const selectors = __INTERACTIVE_SELECTORS__;
    const markers = [];
__SCOPE_WALKER__
    awWalkScopes(document, 0, function (scope, frameDepth) {
        selectors.forEach(function (selector) {
            scope.querySelectorAll(selector).forEach(function (element) {
                // Skip already marked elements
                if (element.hasAttribute('data-autowing-id')) {
                    return;
                }

                const uniqueId = generateUniqueId();
                element.setAttribute('data-autowing-id', uniqueId);

                markers.push({
                    id: uniqueId,
                    tagName: element.tagName.toLowerCase(),
                    type: element.getAttribute('type') || null,
                    placeholder: element.getAttribute('placeholder') || null,
                    value: element.value || null,
                    textContent: element.textContent ? element.textContent.trim().substring(0, 100) : '',
                    ariaLabel: element.getAttribute('aria-label') || null,
                    role: element.getAttribute('role') || null,
                    inFrame: frameDepth > 0,
                    boundingBox: element.getBoundingClientRect()
                });
            });
        });
    });

    return markers;
})();
"""

_ELEMENTS_SCRIPT_TEMPLATE = """
(() => {
    const selectors = __ELEMENT_SELECTORS__;
    const elements = [];
__SCOPE_WALKER__
    awWalkScopes(document, 0, function (scope, frameDepth) {
        selectors.forEach(function (selector) {
            scope.querySelectorAll(selector).forEach(function (el) {
                if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                    elements.push({
                        tag: el.tagName.toLowerCase(),
                        type: el.getAttribute('type') || null,
                        placeholder: el.getAttribute('placeholder') || null,
                        value: el.value || null,
                        text: el.textContent ? el.textContent.trim() : '',
                        aria: el.getAttribute('aria-label') || null,
                        id: el.id || '',
                        name: el.getAttribute('name') || null,
                        // SVG elements expose a non-string className; keep it serializable
                        class: typeof el.className === 'string' ? el.className : '',
                        draggable: el.getAttribute('draggable') || null,
                        autowingId: el.getAttribute('data-autowing-id') || null,
                        inFrame: frameDepth > 0,
                        // Note: for elements inside iframes the box is relative
                        // to that frame's viewport
                        boundingBox: {
                            x: el.getBoundingClientRect().x,
                            y: el.getBoundingClientRect().y,
                            width: el.getBoundingClientRect().width,
                            height: el.getBoundingClientRect().height
                        }
                    });
                }
            });
        });
    });

    return elements;
})();
"""

_CLEAR_MARKERS_SCRIPT_TEMPLATE = """
(() => {
__SCOPE_WALKER__
    awWalkScopes(document, 0, function (scope) {
        scope.querySelectorAll('[data-autowing-id]').forEach(function (el) {
            el.removeAttribute('data-autowing-id');
        });
    });
})();
"""


def _fill_script_template(template: str) -> str:
    """Fill shared placeholders and return the script as a single IIFE expression."""
    return (template
            .replace("__INTERACTIVE_SELECTORS__", _INTERACTIVE_SELECTORS_JS)
            .replace("__ELEMENT_SELECTORS__", _ELEMENT_SELECTORS_JS)
            .replace("__SCOPE_WALKER__", _SCOPE_WALKER_JS)
            .strip())


def build_marker_injection_script() -> str:
    """
    Build the marker injection script (IIFE expression returning the marker
    list). Covers the top document, same-origin iframes and open shadow roots.
    """
    return _fill_script_template(_MARKER_SCRIPT_TEMPLATE)


def build_elements_collection_script() -> str:
    """
    Build the element collection script (IIFE expression returning visible
    elements). Covers the top document, same-origin iframes and open shadow
    roots; nested-frame elements carry ``inFrame: true``.
    """
    return _fill_script_template(_ELEMENTS_SCRIPT_TEMPLATE)


def build_clear_markers_script() -> str:
    """Build the script that removes all data-autowing-id markers, including
    those inside same-origin iframes and open shadow roots."""
    return _fill_script_template(_CLEAR_MARKERS_SCRIPT_TEMPLATE)


class AiFixtureWeb(AiFixtureBase, ABC):
    """
    Abstract base class for web automation fixtures.
    Provides common functionality for both Playwright and Selenium implementations.
    """
    
    def __init__(self):
        """Initialize the web automation fixture."""
        super().__init__()
        self._element_markers = {}  # Store element marker mappings
        self._inject_markers_enabled = True  # Control whether to enable marker injection

    def _inject_element_markers(self) -> None:
        """
        Inject unique identifiers into interactive elements on the page
        This feature is inspired by browser-use design philosophy
        """
        if not self._inject_markers_enabled:
            return
            
        try:
            markers = self._execute_marker_injection_script()
            
            # Always ensure we have a list
            if not isinstance(markers, list):
                markers = []
            
            # Update marker mapping
            for marker in markers:
                if isinstance(marker, dict) and 'id' in marker:
                    self._element_markers[marker['id']] = marker
                
            logger.debug(f"💉 Injected {len(markers)} element markers")
            
        except Exception as e:
            logger.warning(f"⚠️ Element marker injection failed: {str(e)}")
            # Ensure we have an empty dict even on failure
            if not hasattr(self, '_element_markers'):
                self._element_markers = {}

    @abstractmethod
    def _execute_marker_injection_script(self) -> Any:
        """
        Execute the JavaScript marker injection script.
        Must be implemented by subclasses.
        
        Returns:
            Any: The result of the JavaScript execution
        """
        pass

    @abstractmethod
    def _get_basic_page_info(self) -> Dict[str, str]:
        """
        Get basic page information (URL, title).
        Must be implemented by subclasses.
        
        Returns:
            Dict[str, str]: Dictionary containing URL and title
        """
        pass

    @abstractmethod
    def _execute_elements_script(self) -> Any:
        """
        Execute JavaScript to get page elements information.
        Must be implemented by subclasses.
        
        Returns:
            Any: The result of the JavaScript execution
        """
        pass

    @abstractmethod
    def _find_element_by_marker(self, marker_id: str):
        """
        Find elements by marker ID.
        Must be implemented by subclasses.
        
        Args:
            marker_id (str): The autowing marker ID of the element
            
        Returns:
            Element locator/object specific to the framework
        """
        pass

    def _get_page_context(self) -> Dict[str, Any]:
        """
        Extract context information from the current page.
        Collects information about visible elements and page metadata.

        Returns:
            Dict[str, Any]: A dictionary containing page URL, title, and information about
                           visible interactive elements
        """
        # Inject element markers
        self._inject_element_markers()
        
        # Get basic page info
        basic_info = self._get_basic_page_info()

        # Get key elements info using JavaScript
        elements_info = self._execute_elements_script()
        
        # Handle cases where execute_script returns None
        if elements_info is None:
            elements_info = []

        return {
            **basic_info,
            "elements": elements_info,
            "elementMarkers": self._element_markers  # Add marker information
        }

    def enable_marker_injection(self, enabled: bool = True):
        """
        Enable or disable element marker injection feature
        
        Args:
            enabled (bool): Whether to enable marker injection
        """
        self._inject_markers_enabled = enabled
        if not enabled:
            self._clear_element_markers()

    @abstractmethod
    def _clear_element_markers_script(self) -> str:
        """
        Get JavaScript code to clear all element markers.
        Must be implemented by subclasses.
        
        Returns:
            str: JavaScript code to clear markers
        """
        pass

    def _clear_element_markers(self):
        """Clear all element markers"""
        try:
            clear_script = self._clear_element_markers_script()
            self._execute_javascript(clear_script)
            self._element_markers.clear()
            logger.debug("🧹 Cleared all element markers")
        except Exception as e:
            logger.warning(f"⚠️ Failed to clear element markers: {str(e)}")

    @abstractmethod
    def _execute_javascript(self, script: str) -> Any:
        """
        Execute JavaScript code.
        Must be implemented by subclasses.
        
        Args:
            script (str): JavaScript code to execute
            
        Returns:
            Any: Result of JavaScript execution
        """
        pass
