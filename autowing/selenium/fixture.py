import json
from typing import Any, Dict, Optional

from loguru import logger
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from autowing.core.ai_fixture_web import AiFixtureWeb
from autowing.core.llm.factory import LLMFactory
from autowing.utils.transition import selector_to_selenium


class SeleniumAiFixture(AiFixtureWeb):
    """
    A fixture class that combines Selenium with AI capabilities for web automation.
    Provides AI-driven interaction with web pages using various LLM providers.
    Maintains API compatibility with PlaywrightAiFixture.
    """

    def __init__(self, driver: WebDriver):
        """
        Initialize the AI-powered Selenium fixture.

        Args:
            driver (WebDriver): The Selenium WebDriver instance to automate
        """
        super().__init__()
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.llm_client = LLMFactory.create()

    def get_cache_statistics(self) -> dict:
        """
        Get cache usage statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        return self.cache_manager.get_statistics()

    def _execute_marker_injection_script(self) -> Any:
        """Execute the JavaScript marker injection script for Selenium."""
        marker_script = """
        (() => {
            // Function to generate unique ID
            function generateUniqueId() {
                return 'aw-' + Math.random().toString(36).substr(2, 9);
            }
            
            // Define element selectors that need marking
            const selectors = [
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
            ];
            
            const markers = [];
            
            selectors.forEach((selector) => {
                const elements = document.querySelectorAll(selector);
                elements.forEach((element) => {
                    // Skip already marked elements
                    if (element.hasAttribute('data-autowing-id')) {
                        return;
                    }
                    
                    // Skip invisible elements
                    if (element.offsetWidth <= 0 || element.offsetHeight <= 0) {
                        return;
                    }
                    
                    // Generate unique ID
                    const uniqueId = generateUniqueId();
                    element.setAttribute('data-autowing-id', uniqueId);
                    
                    // Collect element information (same as Playwright)
                    markers.push({
                        id: uniqueId,
                        tagName: element.tagName.toLowerCase(),
                        type: element.getAttribute('type') || null,
                        placeholder: element.getAttribute('placeholder') || null,
                        value: element.value || null,
                        textContent: element.textContent ? element.textContent.trim().substring(0, 100) : '',
                        ariaLabel: element.getAttribute('aria-label') || null,
                        role: element.getAttribute('role') || null,
                        boundingBox: {
                            x: element.getBoundingClientRect().x,
                            y: element.getBoundingClientRect().y,
                            width: element.getBoundingClientRect().width,
                            height: element.getBoundingClientRect().height
                        }
                    });
                });
            });
            
            return markers;
        })();
        """
        return self.driver.execute_script(marker_script)

    def _get_basic_page_info(self) -> Dict[str, str]:
        """Get basic page information for Selenium."""
        return {
            "url": self.driver.current_url,
            "title": self.driver.title
        }

    def _execute_elements_script(self) -> Any:
        """Execute JavaScript to get page elements information for Selenium."""
        elements_script = """
            return (function() {
                var getVisibleElements = function() {
                    var elements = [];
                    var selectors = [
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
                    ];
                    
                    selectors.forEach(function(selector) {
                        var els = document.querySelectorAll(selector);
                        els.forEach(function(el) {
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
                                    class: el.className || '',
                                    draggable: el.getAttribute('draggable') || null,
                                    // New addition: include autowing marker ID
                                    autowingId: el.getAttribute('data-autowing-id') || null,
                                    // New addition: element position information
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
                    return elements;
                };
                return getVisibleElements();
            })();
        """
        return self.driver.execute_script(elements_script)

    def _find_element_by_marker(self, marker_id: str):
        """
        Find elements by marker ID for Selenium.
        
        Args:
            marker_id (str): The autowing marker ID of the element
            
        Returns:
            WebElement: Selenium element object
        """
        try:
            return self.driver.find_element(By.CSS_SELECTOR, f'[data-autowing-id="{marker_id}"]')
        except:
            # Fallback to wait for elements
            return self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-autowing-id="{marker_id}"]'))
            )

    def _clear_element_markers_script(self) -> str:
        """Get JavaScript code to clear all element markers for Selenium."""
        return """
            var elements = document.querySelectorAll('[data-autowing-id]');
            elements.forEach(function(el) {
                el.removeAttribute('data-autowing-id');
            });
        """

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
    "action": "fill|click|press (REQUIRED)", 
    "value": "text for fill action (optional)",
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
            raise ValueError(f"Failed to generate test cases. Error: {str(e)}\nResponse: {cleaned_response[:100]}...")


def create_fixture():
    """
    Create a SeleniumAiFixture factory.
    """
    return SeleniumAiFixture
