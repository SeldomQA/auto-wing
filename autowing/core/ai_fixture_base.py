from typing import Any

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
