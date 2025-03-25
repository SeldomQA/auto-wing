from typing import Any

from autowing.core.cache.cache_manager import CacheManager


class AiFixtureBase:
    """
    Base class for AI Fixtures. Contains common response processing logic
    shared between Playwright and Selenium fixtures.
    """

    def __init__(self):
        """Initialize the base fixture with cache support."""
        self.cache_manager = CacheManager()

    def _remove_empty_keys(self, dict_list: list) -> list:
        """
        remove element keys, Reduce tokens use.
        :return:
        """
        if not dict_list:
            return []

        new_list = []
        for d in dict_list:
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
        response = response.strip()
        if '```' in response:
            # Prioritize handling ```json format
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            else:
                response = response.split('```')[1].split('```')[0].strip()
            # If the cleaned response starts with "json" or "python", remove the first line description
            if response.startswith(('json', 'python')):
                parts = response.split('\n', 1)
                if len(parts) > 1:
                    response = parts[1].strip()
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

        if format_hint == 'object[]':
            if not isinstance(result, list):
                result = [result]
            if not all(isinstance(item, dict) for item in result):
                raise ValueError(f"Not all items are objects: {result}")
            return result

        return result

    def _get_cached_or_compute(self, prompt: str, context: dict, compute_func) -> Any:
        """
        Get response from cache or compute it using the provided function.
        
        Args:
            prompt: The prompt to generate cache key
            context: The context to generate cache key
            compute_func: Function to compute response if not cached
        """
        # Try to get from cache first
        cached_response = self.cache_manager.get(prompt, context)
        if cached_response is not None:
            return cached_response

        # Compute response if not cached
        response = compute_func()

        # Cache the computed response
        self.cache_manager.set(prompt, context, response)

        return response
