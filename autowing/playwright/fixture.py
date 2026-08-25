import base64
import json
from typing import Any, Dict, Optional

from loguru import logger
from playwright.sync_api import Frame, FrameLocator, Locator, Page

from autowing.core.ai_fixture_web import (
    AiFixtureWeb,
    build_clear_markers_script,
    build_elements_collection_script,
    build_marker_injection_script,
)
from autowing.core.llm.factory import LLMFactory
from autowing.utils.transition import selector_to_locator


class PlaywrightAiFixture(AiFixtureWeb):
    """
    A fixture class that combines Playwright with AI capabilities for web automation.
    Provides AI-driven interaction with web pages using various LLM providers.
    """

    def __init__(self, page: Page, llm_client=None):
        """
        Initialize the AI-powered Playwright fixture.

        Args:
            page (Page): The Playwright page object to automate
            llm_client: Optional BaseLLMClient implementation to inject
                        instead of LLMFactory.create() - primarily for
                        offline testing with a scripted fake (plan item T4)
        """
        super().__init__()
        self.page = page
        self.llm_client = llm_client if llm_client is not None else LLMFactory.create()

    def get_cache_statistics(self) -> dict:
        """
        Get cache usage statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        return self.cache_manager.get_statistics()

    def _execute_marker_injection_script(self) -> Any:
        """Execute the shared marker injection script (covers same-origin
        iframes and open shadow roots)."""
        return self.page.evaluate(build_marker_injection_script())

    def _get_basic_page_info(self) -> Dict[str, str]:
        """Get basic page information for Playwright."""
        return {
            "url": self.page.url,
            "title": self.page.title()
        }

    def _execute_elements_script(self) -> Any:
        """Execute the shared element collection script (covers same-origin
        iframes and open shadow roots)."""
        return self.page.evaluate(build_elements_collection_script())

    def _find_element_by_marker(self, marker_id: str):
        """
        Find elements by marker ID for Playwright.
        
        Args:
            marker_id (str): The autowing marker ID of the element
            
        Returns:
            Locator: Playwright element locator
        """
        selector = f'[data-autowing-id="{marker_id}"]'
        return self.page.locator(selector)

    def _clear_element_markers_script(self) -> str:
        """Get JavaScript code to clear all element markers for Playwright."""
        return build_clear_markers_script()

    def _execute_javascript(self, script: str) -> Any:
        """Execute JavaScript code for Playwright."""
        return self.page.evaluate(script)

    def _capture_screenshot_base64(self) -> Optional[str]:
        """Capture the current page viewport as a base64-encoded PNG image."""
        return base64.b64encode(self.page.screenshot()).decode('utf-8')

    def _resolve_frame(self, frame):
        """
        Resolve a frame reference into a Playwright Frame.

        Args:
            frame: A Frame (returned as-is), a FrameLocator / Locator pointing
                   at the iframe element, or a CSS/XPath selector string for it

        Returns:
            Frame: The resolved frame

        Raises:
            ValueError: If a locator cannot be resolved to a frame
            TypeError: If the frame reference type is unsupported
        """
        if frame is None:
            return None
        if isinstance(frame, str):
            frame = self.page.frame_locator(frame)
        if isinstance(frame, Frame):
            return frame
        if isinstance(frame, FrameLocator):
            frame = frame.owner
        if isinstance(frame, Locator):
            # NOTE: Locator.content_frame() is broken in the sync API of some
            # playwright versions ('FrameLocator' object is not callable), so
            # resolve through the element handle instead.
            handle = frame.element_handle()
            if handle is None:
                raise ValueError("Could not resolve frame: locator matched no element")
            resolved = handle.content_frame()
            if resolved is None:
                raise ValueError("Could not resolve frame: element is not an iframe")
            return resolved
        raise TypeError(f"Unsupported frame reference: {type(frame)!r}")

    def ai_action(self, prompt: str, frame=None, **kwargs) -> None:
        """
        Execute an AI-driven action on the page based on the given prompt.

        Failed attempts trigger a re-plan: the LLM is called again with the
        error as extra context (up to AUTOWING_MAX_RETRIES, default 2).
        A replanned instruction that succeeds replaces the cached one.

        Args:
            prompt (str): Natural language description of the action to perform
            frame: Optional frame scope for the action - a Frame, FrameLocator,
                   Locator pointing at the iframe element, or a selector string.
                   When given, the resolved selector is located within that
                   frame instead of the whole page.
            **kwargs: Additional arguments for framework-specific implementations

        Raises:
            ValueError: If the AI response cannot be parsed or contains invalid instructions
        """
        logger.info(f"🪽 AI Action: {prompt}")
        target_frame = self._resolve_frame(frame)
        context = self._get_page_context()
        context["elements"] = self._remove_empty_keys(context.get("elements", []))

        def validate_instruction(result):
            # Strict validation of required fields
            for field in ('selector', 'action'):
                if field not in result:
                    raise ValueError(f"Missing required field '{field}'. Got fields: {list(result.keys())}")
            return result

        def compute_action(error_hint: str = "") -> dict:
            # Most strict prompt, force specific field names
            action_prompt = f"""
You are a web automation assistant. Generate EXACT JSON with these SPECIFIC field names:

REQUIRED JSON FORMAT:
{{
    "selector": "CSS selector or XPath (REQUIRED)",
    "action": "fill|click|press|select|hover|check|uncheck|scroll|upload (REQUIRED)", 
    "value": "text for fill / option value or label for select / file path for upload (optional)",
    "key": "key for press action (optional)"
}}

CURRENT CONTEXT:
URL: {context['url']}
Elements: {json.dumps(context['elements'], indent=2)}

REQUEST: {prompt}

STRICT RULES:
1. ONLY return the JSON object above
2. MUST include "selector" and "action" fields
3. NO explanations, NO other text
4. Use EXACT field names shown above

EXAMPLE:
{{"selector": "input#sb_form_q", "action": "fill", "value": "playwright", "key": "Enter"}}

RESPONSE (JSON ONLY):
"""
            if error_hint:
                action_prompt += f"""
NOTICE: A previous attempt on this page failed with: {error_hint}
Re-plan carefully to avoid the same problem.
"""
            return self._llm_json_with_retry(action_prompt, validate_instruction)

        if target_frame is not None:
            execute_action = (lambda instruction, from_cache:
                              self._execute_action_instruction(instruction, from_cache,
                                                               frame=target_frame))
        else:
            execute_action = self._execute_action_instruction
        self._ai_action_loop(prompt, context, compute_action, execute_action)

    def _execute_action_instruction(self, instruction: dict, from_cache: bool = False,
                                    frame=None) -> None:
        """
        Execute one parsed ai_action instruction on the page.

        Args:
            instruction (dict): Parsed LLM instruction (selector/action/value/key)
            from_cache (bool): Whether the instruction came from the cache
            frame: Optional Playwright Frame to scope locator resolution to

        Supported actions: click, fill, press, select, hover, check, uncheck,
        scroll (into view), upload (set_input_files).

        Every element operation is capped by AUTOWING_ACTION_TIMEOUT
        (default 30s) so a stuck element fails fast into the retry loop
        instead of hanging on playwright's own defaults.

        Raises:
            ValueError: If the instruction is invalid or the cached selector is stale
        """
        selector = instruction.get('selector')
        action = instruction.get('action')

        if not selector or not action:
            raise ValueError("Invalid instruction format")

        timeout_ms = int(getattr(self, '_action_timeout', 30) * 1000)

        # Perform the action
        selector = selector_to_locator(selector)
        scope = frame if frame is not None else self.page
        element = scope.locator(selector)

        # Stale-cache guard: a cached selector may no longer exist after a
        # page redesign. Fail fast so the retry loop can re-plan.
        if from_cache and element.count() == 0:
            raise ValueError(f"Cached selector matched no elements: {selector}")

        if action == 'click':
            element.click(timeout=timeout_ms)
        elif action == 'fill':
            element.fill(instruction.get('value', ''), timeout=timeout_ms)
            if instruction.get('key'):
                element.press(instruction.get('key'), timeout=timeout_ms)
        elif action == 'press':
            element.press(instruction.get('key', 'Enter'), timeout=timeout_ms)
        elif action == 'select':
            option_value = instruction.get('value')
            if option_value is None:
                raise ValueError("select action requires 'value' (option value or label)")
            try:
                element.select_option(value=str(option_value), timeout=timeout_ms)
            except Exception:
                # Retry by visible label when no option carries that value
                element.select_option(label=str(option_value), timeout=timeout_ms)
        elif action == 'hover':
            element.hover(timeout=timeout_ms)
        elif action == 'check':
            element.check(timeout=timeout_ms)
        elif action == 'uncheck':
            element.uncheck(timeout=timeout_ms)
        elif action == 'scroll':
            element.scroll_into_view_if_needed(timeout=timeout_ms)
        elif action == 'upload':
            file_path = instruction.get('value')
            if not file_path:
                raise ValueError("upload action requires 'value' (file path)")
            element.set_input_files(file_path, timeout=timeout_ms)
        else:
            raise ValueError(f"Unsupported action: {action}")

    def ai_function_cases(self, prompt: str, language: str = "Chinese") -> str:
        """
        Generate functional test cases based on the given prompt.
        
        Args:
            prompt (str): Natural language description of the functionality to test
            language (str): Natural language description of the functionality to test

        Returns:
            str: Generated test cases in a standard format
        
        Raises:
            ValueError: If the AI response cannot be parsed or contains invalid instructions
        """
        logger.info(f"🪽 AI Function Case: {prompt}")
        context = self._get_page_context()

        format_hint = ""
        if prompt.startswith(('json[]', 'markdown[]')):
            format_hint = prompt.split(',')[0].strip()
            prompt = ','.join(prompt.split(',')[1:]).strip()

        # Provide different prompts based on the format
        if format_hint == 'json[]':
            # Construct the prompt for generating test cases
            case_prompt = f"""
You are a web automation assistant. Based on the following page context, generate functional test cases.

Current page context:
URL: {context['url']}
Title: {context['title']}

Available elements:
{json.dumps(context['elements'], indent=2)}

User request: {prompt}

Return ONLY the test cases in the following format, no other text:
[
    {{
      "Test Case ID": "001",
      "Steps": "Describe the steps to perform the test without mentioning element locators.",
      "Expected Result": "Describe the expected result."
    }},
    {{
      "Test Case ID": "002",
      "Steps": "Describe the steps to perform the test without mentioning element locators.",
      "Expected Result": "Describe the expected result."
    }}
]
...

Finally, the output result is required to be in {language}
"""
        elif format_hint == 'markdown[]':
            case_prompt = f"""
You are a web automation assistant. Based on the following page context, generate functional test cases.

Current page context:
URL: {context['url']}
Title: {context['title']}

Available elements:
{json.dumps(context['elements'], indent=2)}

User request: {prompt}

Return ONLY the test cases in the following format, no other text:
| Test Case ID | Steps                                             | Expected Result               |
|--------------|---------------------------------------------------|-------------------------------|
| 001          | Describe the steps to perform the test without mentioning element locators. | Describe the expected result. |
| 002          | Describe the steps to perform the test without mentioning element locators. | Describe the expected result. |
...

Finally, the output result is required to be in {language}
"""
        else:
            case_prompt = f"""
You are a web automation assistant. Based on the following page context, generate functional test cases.

Current page context:
URL: {context['url']}
Title: {context['title']}

Available elements:
{json.dumps(context['elements'], indent=2)}

User request: {prompt}

Return ONLY the test cases in the following format, no other text:
Test Case ID: 001
Steps: Describe the steps to perform the test without mentioning element locators.
Expected Result: Describe the expected result.

Test Case ID: 002
Steps: Describe the steps to perform the test without mentioning element locators.
Expected Result: Describe the expected result.

...

Finally, the output result is required to be in {language}
"""

        cleaned_response = ""
        try:
            response = self._llm_complete(case_prompt)
            cleaned_response = self._clean_response(response)

            logger.debug(f"""📄 Function Cases:\n {cleaned_response}""")
            return cleaned_response
        except Exception as e:
            raise ValueError(f"Failed to generate test cases. Error: {str(e)}\nResponse: {cleaned_response[:100]}...") from e


def create_fixture():
    """
    Create a PlaywrightAiFixture factory.

    Returns:
        Callable[[Page], PlaywrightAiFixture]: A factory function that creates
        PlaywrightAiFixture instances
    """
    return PlaywrightAiFixture
