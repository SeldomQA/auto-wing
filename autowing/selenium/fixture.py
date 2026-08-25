import json
from typing import Any, Dict, Optional

from loguru import logger
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from autowing.core.ai_fixture_web import (
    AiFixtureWeb,
    build_clear_markers_script,
    build_elements_collection_script,
    build_marker_injection_script,
)
from autowing.core.llm.factory import LLMFactory
from autowing.utils.transition import selector_to_selenium


class SeleniumAiFixture(AiFixtureWeb):
    """
    A fixture class that combines Selenium with AI capabilities for web automation.
    Provides AI-driven interaction with web pages using various LLM providers.
    Maintains API compatibility with PlaywrightAiFixture.
    """

    def __init__(self, driver: WebDriver, llm_client=None):
        """
        Initialize the AI-powered Selenium fixture.

        Args:
            driver (WebDriver): The Selenium WebDriver instance to automate
            llm_client: Optional BaseLLMClient implementation to inject
                        instead of LLMFactory.create() - primarily for
                        offline testing with a scripted fake (plan item T4)
        """
        super().__init__()
        self.driver = driver
        # Element waits are capped by AUTOWING_ACTION_TIMEOUT (default 30s)
        # so a stuck element fails fast into the retry/re-plan loop.
        self.wait = WebDriverWait(driver, self._action_timeout)
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
        # NOTE: "return" must stay on the same line as the IIFE expression,
        # otherwise JavaScript ASI turns it into "return;".
        return self.driver.execute_script("return " + build_marker_injection_script())

    def _get_basic_page_info(self) -> Dict[str, str]:
        """Get basic page information for Selenium."""
        return {
            "url": self.driver.current_url,
            "title": self.driver.title
        }

    def _execute_elements_script(self) -> Any:
        """Execute the shared element collection script (covers same-origin
        iframes and open shadow roots)."""
        # NOTE: "return" must stay on the same line as the IIFE expression,
        # otherwise JavaScript ASI turns it into "return;".
        return self.driver.execute_script("return " + build_elements_collection_script())

    def _find_element_by_marker(self, marker_id: str):
        """
        Find elements by marker ID for Selenium.
        
        Args:
            marker_id (str): The autowing marker ID of the element
            
        Returns:
            WebElement: Selenium element object
        """
        selector = f'[data-autowing-id="{marker_id}"]'
        try:
            return self.driver.find_element(By.CSS_SELECTOR, selector)
        except Exception:
            # Markers may live inside nested frames reached by the shared
            # injection script; find_element only searches the current frame.
            found = self._find_in_frames(By.CSS_SELECTOR, selector)
            if found is not None:
                return found
            # Fallback to wait for elements
            return self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )

    def _find_in_frames(self, by: str, value: str):
        """
        Recursively search child frames for an element.

        When found, the driver stays switched into the containing frame so
        the caller can interact with the element directly. When not found,
        the frame state is restored before returning.

        Args:
            by (str): Selenium By strategy
            value (str): Locator value

        Returns:
            Optional[WebElement]: The element, or None when not found
        """
        frames = (self.driver.find_elements(By.TAG_NAME, 'iframe')
                  + self.driver.find_elements(By.TAG_NAME, 'frame'))
        for frame in frames:
            try:
                self.driver.switch_to.frame(frame)
            except Exception:
                continue
            found = self.driver.find_elements(by, value)
            if found:
                return found[0]
            deeper = self._find_in_frames(by, value)
            if deeper is not None:
                return deeper
            self.driver.switch_to.parent_frame()
        return None

    def _clear_element_markers_script(self) -> str:
        """Get JavaScript code to clear all element markers for Selenium."""
        return build_clear_markers_script()

    def _execute_javascript(self, script: str) -> Any:
        """Execute JavaScript code for Selenium."""
        return self.driver.execute_script(script)

    def _capture_screenshot_base64(self) -> Optional[str]:
        """Capture the current page viewport as a base64-encoded PNG image."""
        return self.driver.get_screenshot_as_base64()

    def _locate_element(self, selector: str):
        """
        Locate an element by XPath first, falling back to CSS selector.

        Args:
            selector (str): XPath or CSS selector

        Returns:
            WebElement: The located element

        Raises:
            TimeoutException: If the element cannot be found by either strategy
        """
        try:
            return self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
        except TimeoutException:
            return self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))

    def ai_action(self, prompt: str) -> None:
        """
        Execute an AI-driven action on the page based on the given prompt.

        Failed attempts trigger a re-plan: the LLM is called again with the
        error as extra context (up to AUTOWING_MAX_RETRIES, default 2).
        A replanned instruction that succeeds replaces the cached one.

        Args:
            prompt (str): Natural language description of the action to perform

        Raises:
            ValueError: If the AI response cannot be parsed or contains invalid instructions
            TimeoutException: If the element cannot be found or interacted with
        """
        logger.info(f"🪽 AI Action: {prompt}")
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
    "selector": "XPATH selector (REQUIRED)",
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
{{"selector": "//input[@id='sb_form_q']", "action": "fill", "value": "playwright", "key": "Enter"}}

RESPONSE (JSON ONLY):
"""
            if error_hint:
                action_prompt += f"""
NOTICE: A previous attempt on this page failed with: {error_hint}
Re-plan carefully to avoid the same problem.
"""
            return self._llm_json_with_retry(action_prompt, validate_instruction)

        self._ai_action_loop(prompt, context, compute_action, self._execute_action_instruction)

    def _execute_action_instruction(self, instruction: dict, from_cache: bool = False) -> None:
        """
        Execute one parsed ai_action instruction on the page.

        Args:
            instruction (dict): Parsed LLM instruction (selector/action/value/key)
            from_cache (bool): Whether the instruction came from the cache

        Supported actions: click, fill, press, select, hover, check, uncheck,
        scroll (into view), upload (send file path to input[type=file]).

        Raises:
            ValueError: If the instruction is invalid
            TimeoutException: If the element cannot be found or interacted with
        """
        selector = instruction.get('selector')
        action = instruction.get('action')

        if not selector or not action:
            raise ValueError("Invalid instruction format")

        # Execute the action
        selector = selector_to_selenium(selector)
        element = self._locate_element(selector)

        if action == 'click':
            element.click()
        elif action == 'fill':
            element.clear()
            element.send_keys(instruction.get('value', ''))
            if instruction.get('key'):
                key_attr = getattr(Keys, instruction['key'].upper(), None)
                if key_attr:
                    element.send_keys(key_attr)
        elif action == 'press':
            key_attr = getattr(Keys, instruction.get('key', 'ENTER').upper())
            element.send_keys(key_attr)
        elif action == 'select':
            option_value = instruction.get('value')
            if option_value is None:
                raise ValueError("select action requires 'value' (option value or label)")
            select = Select(element)
            try:
                select.select_by_value(str(option_value))
            except Exception:
                # Retry by visible text when no option carries that value
                select.select_by_visible_text(str(option_value))
        elif action == 'hover':
            ActionChains(self.driver).move_to_element(element).perform()
        elif action in ('check', 'uncheck'):
            wanted = (action == 'check')
            if element.is_selected() != wanted:
                element.click()
        elif action == 'scroll':
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element)
        elif action == 'upload':
            file_path = instruction.get('value')
            if not file_path:
                raise ValueError("upload action requires 'value' (file path)")
            element.send_keys(file_path)
        else:
            raise ValueError(f"Unsupported action: {action}")

        logger.info(f"✅ Action executed successfully: {action}")

    def ai_function_cases(self, prompt: str, language: str = "Chinese") -> str:
        """
        Generate functional test cases based on the given prompt.
        
        Args:
            prompt (str): Natural language description of the functionality to test
            language (str): Language in which the test cases should be generated
        
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
    Create a SeleniumAiFixture factory.
    """
    return SeleniumAiFixture
