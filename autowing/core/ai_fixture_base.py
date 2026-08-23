import json
import os
from typing import Any, Optional

from loguru import logger

from autowing.core.cache.cache_manager import get_intelligent_cache_manager


class AiFixtureBase:
    """
    Base class for AI Fixtures. Contains common response processing logic
    shared between Playwright, Selenium and Appium fixtures.
    """

    def __init__(self):
        """Initialize the base fixture with intelligent cache support."""
        # Share one cache manager per cache_dir across all fixtures so the
        # TF-IDF index is built once and cache hits work across test cases.
        cache_dir = os.getenv("AUTOWING_CACHE_DIR", ".auto-wing/cache")
        self.cache_manager = get_intelligent_cache_manager(cache_dir=cache_dir)
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

    def _parse_format_hint(self, prompt: str) -> tuple:
        """
        Extract a leading format hint (e.g. 'string[]') from the prompt.

        Args:
            prompt (str): The raw query prompt

        Returns:
            tuple: (format_hint, remaining prompt). format_hint is '' when absent
        """
        if prompt.startswith(('string[]', 'number[]', 'object[]')):
            parts = prompt.split(',', 1)
            return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else '')
        return '', prompt

    @staticmethod
    def _get_context_summary(context: dict) -> str:
        """
        Build prompt header lines from known context keys so that web drivers
        (url/title) and app drivers (activity/package) share one code path.
        """
        lines = []
        if context.get('url'):
            lines.append(f"Page: {context['url']}")
        if context.get('title'):
            lines.append(f"Title: {context['title']}")
        if context.get('activity'):
            lines.append(f"Activity: {context['activity']}")
        if context.get('package'):
            lines.append(f"Package: {context['package']}")
        return "\n".join(lines)

    def _llm_prompt_notice(self) -> str:
        """
        Extra prompt notice appended to query/assert prompts.
        Overridden by the Appium fixture to hint about label/text keys.
        """
        return ""

    def _build_query_prompt(self, context: dict, query: str, format_hint: str) -> str:
        """Build the ai_query prompt for the requested format."""
        ctx_summary = self._get_context_summary(context)
        elements = json.dumps(context.get('elements', []), ensure_ascii=False)
        notice = self._llm_prompt_notice()

        if format_hint == 'string[]':
            return f"""
Extract text content matching the query. Return ONLY a JSON array of strings.

{ctx_summary}
Elements: {elements}
Query: {query}

Return format example: ["result1", "result2"]
{notice}
No other text or explanation.
"""
        if format_hint == 'number[]':
            return f"""
Extract numeric values matching the query. Return ONLY a JSON array of numbers.

{ctx_summary}
Elements: {elements}
Query: {query}

Return format example: [1, 2, 3]
{notice}
No other text or explanation.
"""
        # Default prompt
        return f"""
Extract information matching the query. Return ONLY in valid JSON format.

{ctx_summary}
Elements: {elements}
Query: {query}

Return format:
- For arrays: ["item1", "item2"]
- For objects: {{"key": "value"}}
- For single value: "text" or number
{notice}
No other text or explanation.
"""

    @staticmethod
    def _extract_query_from_text(cleaned_response: str, query: str, format_hint: str) -> Optional[list]:
        """
        Fallback extraction for 'string[]' queries when the LLM response is
        not valid JSON. Returns a deduplicated list, or None when nothing found.
        """
        if format_hint != 'string[]':
            return None

        lines = [line.strip() for line in cleaned_response.split('\n')
                 if line.strip() and not line.startswith(('-', '*', '#'))]

        # Extract lines containing query terms
        query_terms = [term.lower() for term in query.split()
                       if len(term) > 2 and term.lower() not in ['the', 'and', 'for']]

        results = []
        for line in lines:
            if any(term in line.lower() for term in query_terms):
                text = line.strip('`"\'- ,')
                if ':' in text:
                    text = text.split(':', 1)[1].strip()
                if text:
                    results.append(text)

        if results:
            # Remove duplicates while preserving order
            seen = set()
            return [x for x in results if not (x in seen or seen.add(x))]
        return None

    @staticmethod
    def _parse_boolean_response(cleaned_response: str) -> bool:
        """Parse a cleaned LLM response into a boolean for ai_assert."""
        if cleaned_response == 'true':
            return True
        if cleaned_response == 'false':
            return False

        # If the response contains other content, try extracting the boolean
        if 'true' in cleaned_response.split():
            return True
        if 'false' in cleaned_response.split():
            return False

        raise ValueError(
            f"Failed to parse assertion result. Response: {cleaned_response[:100]}... "
            "Response must be 'true' or 'false'"
        )

    def ai_query(self, prompt: str) -> Any:
        """
        Query information from the page/screen using AI analysis.
        Shared implementation for all drivers (Playwright / Selenium / Appium).

        Args:
            prompt (str): Natural language query about the page content.
                         It can include format hints like 'string[]' or 'number[]'.

        Returns:
            Any: The query results in the requested format

        Raises:
            ValueError: If the AI response cannot be parsed into the requested format
        """
        logger.info(f"🪽 AI Query: {prompt}")
        context = self._get_page_context()
        context["elements"] = self._remove_empty_keys(context.get("elements", []))

        format_hint, query = self._parse_format_hint(prompt)
        query_prompt = self._build_query_prompt(context, query, format_hint)

        response = self._llm_complete(query_prompt)

        cleaned_response = ""
        try:
            cleaned_response = self._clean_response(response)
            try:
                result = json.loads(cleaned_response)
                query_info = self._validate_result_format(result, format_hint)
                logger.debug(f"📄 Query: {query_info}")
                return query_info
            except json.JSONDecodeError:
                # Fallback: try extracting from plain text
                extracted = self._extract_query_from_text(cleaned_response, query, format_hint)
                if extracted:
                    logger.debug(f"📄 Query: {extracted}")
                    return extracted
                raise ValueError(f"Failed to parse response as JSON: {cleaned_response[:100]}...")

        except Exception as e:
            raise ValueError(f"Query failed. Error: {str(e)}\nResponse: {cleaned_response[:100]}...")

    def ai_assert(self, prompt: str) -> bool:
        """
        Verify a condition on the page/screen using AI analysis.
        Shared implementation for all drivers (Playwright / Selenium / Appium).

        Args:
            prompt (str): Natural language description of the condition to verify

        Returns:
            bool: True if the condition is met, False otherwise

        Raises:
            ValueError: If the AI response cannot be parsed as a boolean value
        """
        logger.info(f"🪽 AI Assert: {prompt}")
        context = self._get_page_context()
        context["elements"] = self._remove_empty_keys(context.get("elements", []))

        notice = self._llm_prompt_notice()
        assert_prompt = f"""
You are a web automation assistant. Verify the following assertion and return ONLY a boolean value.

{self._get_context_summary(context)}
Elements: {json.dumps(context['elements'], ensure_ascii=False)}

Assertion: {prompt}

{notice}
IMPORTANT: Return ONLY the word 'true' or 'false' (lowercase). No other text, no explanation.
"""

        response = self._llm_complete(assert_prompt)
        cleaned_response = self._clean_response(response).lower()
        return self._parse_boolean_response(cleaned_response)

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
