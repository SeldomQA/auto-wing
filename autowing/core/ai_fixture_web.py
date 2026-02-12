"""
Common base class for web automation fixtures that provides shared functionality
for both Playwright and Selenium implementations.
"""
from typing import Any, Dict
from abc import ABC, abstractmethod

from loguru import logger
from autowing.core.ai_fixture_base import AiFixtureBase


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
