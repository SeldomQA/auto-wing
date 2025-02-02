from typing import Any


class AiFixtureBase:
    """
    Base class for AI Fixtures. Contains common response processing logic
    shared between Playwright and Selenium fixtures.
    """

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