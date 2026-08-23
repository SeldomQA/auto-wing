import os
from typing import Any, Optional

from loguru import logger

from autowing.core.cache.cache_manager import IntelligentCacheManager


class AiFixtureBase:
    """
    Base class for AI Fixtures. Contains common response processing logic
    shared between Playwright and Selenium fixtures.
    """

    def __init__(self):
        """Initialize the base fixture with intelligent cache support."""
        self.cache_manager = IntelligentCacheManager()
        # Vision mode switch: enabled via AUTOWING_VISION env var or enable_vision()
        self._vision_enabled = os.getenv("AUTOWING_VISION", "false").lower() in ("1", "true", "yes")

    def enable_vision(self, enabled: bool = True):
        """
        Enable or disable vision mode for LLM calls.

        When enabled, a screenshot of the current page/screen is attached to the
        prompt so that vision-capable models can ground their answers visually.
        If the model doesn't support vision or the screenshot fails, the call
        automatically falls back to text-only mode.

        Args:
            enabled (bool): Whether to enable vision mode
        """
        self._vision_enabled = enabled

    def _capture_screenshot_base64(self) -> Optional[str]:
        """
        Capture the current page/screen as a base64-encoded PNG image.

        Subclasses backed by a real driver should override this method.

        Returns:
            Optional[str]: Base64 image data, or None if capture is unavailable
        """
        return None

    @staticmethod
    def _build_vision_messages(prompt: str, screenshot_b64: str) -> list:
        """
        Build OpenAI-style multimodal messages for vision completion.

        Args:
            prompt (str): The text prompt
            screenshot_b64 (str): Base64-encoded screenshot

        Returns:
            list: Messages list compatible with complete_with_vision()
        """
        return [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}
                }
            ]
        }]

    def _llm_complete(self, prompt: str) -> str:
        """
        Unified LLM completion entry point with optional vision support.

        When vision mode is enabled, attaches a screenshot and calls
        complete_with_vision(); on any failure (unsupported model, capture
        error, API error) it automatically falls back to text-only complete().

        Args:
            prompt (str): The text prompt to complete

        Returns:
            str: The model's response text
        """
        if self._vision_enabled:
            try:
                screenshot_b64 = self._capture_screenshot_base64()
                if screenshot_b64:
                    messages = self._build_vision_messages(prompt, screenshot_b64)
                    return self.llm_client.complete_with_vision({"messages": messages})
                logger.warning("⚠️ Vision enabled but screenshot capture unavailable, using text mode")
            except Exception as e:
                logger.warning(f"⚠️ Vision completion failed, falling back to text mode: {e}")
        return self.llm_client.complete(prompt)

    def _remove_empty_keys(self, dict_list: list) -> list:
        """
        remove element keys, Reduce tokens use.
        :return:
        """
        if not dict_list:
            return []

        new_list = []
        for d in dict_list:
            # Skip None values
            if d is None:
                continue
            new_dict = {k: v for k, v in d.items() if v != '' and v is not None}
            new_list.append(new_dict)

        return new_list

    def _clean_response(self, response: str) -> str:
        """
        Clean the response text by stripping markdown formatting.
        
        Args:
            response (str): Raw response from LLM

        Returns:
            str: Cleaned response text.
        """
        if not response or not isinstance(response, str):
            return ""

        response = response.strip()

        # Debug logging
        original_length = len(response)
        logger.debug(f"🧹 Starting response cleaning, original length: {original_length}")

        if '```' in response:
            # Prioritize handling ```json format
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
                logger.debug("🔧 Detected ```json format, extracted JSON content")
            else:
                # Handle other code blocks
                parts = response.split('```')
                if len(parts) >= 3:
                    response = parts[1].strip()
                    logger.debug("🔧 Detected code block format, extracted content")
            # If the cleaned response starts with "json" or "python", remove the first line description
            if response.startswith(('json', 'python')):
                parts = response.split('\n', 1)
                if len(parts) > 1:
                    response = parts[1].strip()
                    logger.debug("🔧 Removed language identifier line")

        # Final cleanup
        response = response.strip()

        return response

    def _validate_result_format(self, result: Any, format_hint: str) -> Any:
        """
        Validate and convert the result to match the requested format.
    
        Args:
            result: The parsed result from AI response.
            format_hint: The requested format (e.g., 'string[]').
    
        Returns:
            The validated and possibly converted result.
    
        Raises:
            ValueError: If the result doesn't match the requested format.
        """
        if not format_hint:
            return result

        if format_hint == 'string[]':
            if not isinstance(result, list):
                result = [str(result)]
            return [str(item) for item in result]

        if format_hint == 'number[]':
            if not isinstance(result, list):
                result = [result]
            try:
                return [float(item) for item in result]
            except (ValueError, TypeError):
                raise ValueError(f"Cannot convert results to numbers: {result}")

    def _get_cached_or_compute(self, prompt: str, context: dict, compute_func) -> Any:
        """
        Get cached result or compute new result.
        
        Args:
            prompt: The prompt used for caching
            context: Context information for caching
            compute_func: Function to compute result if not cached
            
        Returns:
            Cached or computed result
        """
        # Try to get from cache first
        cached_response = self.cache_manager.get_intelligent(prompt, context)
        if cached_response is not None:
            return cached_response

        # Compute new result
        try:
            response = compute_func()
            # Cache the result
            self.cache_manager.set_intelligent(prompt, context, response)
            return response
        except Exception as e:
            logger.error(f"❌ Computation function execution failed: {e}")
            raise
