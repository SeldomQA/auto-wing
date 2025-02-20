import json
import re
from typing import Any, Dict

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from loguru import logger
from selenium.webdriver.support.ui import WebDriverWait

from autowing.appium.actions import Action
from autowing.core.ai_fixture_base import AiFixtureBase
from autowing.core.llm.factory import LLMFactory


class AppiumAiFixture(AiFixtureBase):
    """
    A fixture class that combines Appium with AI capabilities for mobile automation.
    Provides AI-driven interaction with mobile apps using various LLM providers.
    """

    def __init__(self, driver: WebDriver):
        """
        Initialize the AI-powered Appium fixture.

        Args:
            driver (WebDriver): The Appium WebDriver instance to automate
        """
        self.driver = driver
        self.llm_client = LLMFactory.create()
        self.wait = WebDriverWait(self.driver, 10)  # Default timeout of 10 seconds

    def _get_page_context(self) -> Dict[str, Any]:
        """
        Extract context information from the current screen of the mobile app.
        Collects information about visible elements and screen metadata.

        Returns:
            Dict[str, Any]: A dictionary containing screen information and visible interactive elements
        """
        # Get basic screen info
        basic_info = {
            "activity": self.driver.current_activity,
            "package": self.driver.current_package
        }

        # Get key elements info using Appium
        elements_info = []
        elements = self.driver.find_elements(AppiumBy.XPATH, "//*")
        for el in elements:
            if el.is_displayed():
                elements_info.append({
                    "tag": el.tag_name,
                    "text": el.text,
                    "resource_id": el.get_attribute("resource-id"),
                    "content_desc": el.get_attribute("content-desc"),
                    "class": el.get_attribute("class"),
                    "bounds": el.get_attribute("bounds")
                })

        return {
            **basic_info,
            "elements": elements_info
        }

    def ai_action(self, prompt: str) -> None:
        """
        Execute an AI-driven action on the screen based on the given prompt.

        Args:
            prompt (str): Natural language description of the action to perform

        Raises:
            ValueError: If the AI response cannot be parsed or contains invalid instructions
            TimeoutException: If the element cannot be found or interacted with
        """
        logger.info(f"🪽 AI Action: {prompt}")
        context = self._get_page_context()

        action_prompt = f"""
Extract element locator and action from the request. Return ONLY a JSON object.

Activity: {context['activity']}
Package: {context['package']}
Elements: {context['elements']}
Request: {prompt}

Return list format:
[{{
    "bounds": "coordinates of the element in the format [x1,y1][x2,y2] (notice, x1,y1 and x2,y2 are replaced by concrete coordinates.)",
    "action": "click/fill/press",
    "value": "text to input if needed",
    "key": "key to press if needed"
}}]

No other text or explanation.
"""

        response = self.llm_client.complete(action_prompt)
        cleaned_response = self._clean_response(response)
        instruction = json.loads(cleaned_response)

        if isinstance(instruction, list) is False:
            raise ValueError("Invalid instruction format")

        for step in instruction:
            bounds = step.get('bounds')
            action = step.get('action')

            if not bounds or not action:
                raise ValueError("Invalid instruction format")

            # Extract coordinates from bounds
            coord = re.findall(r'\d+', bounds)
            x1, y1, x2, y2 = map(int, coord)
            x_center = (x1 + x2) // 2
            y_center = (y1 + y2) // 2

            # Execute the action
            if action == 'click':
                action = Action(self.driver)
                action.tap(x=x_center, y=y_center)
            elif action == 'fill':
                fill_text = step.get('value', '')
                logger.info(f"⌨️ fill text: {fill_text}.")
                self.driver.execute_script('mobile: type', {'text': fill_text})
            elif action == 'press':
                logger.info("🔍 keyboard search key.")
                self.driver.execute_script('mobile: performEditorAction', {'action': 'search'})
            else:
                raise ValueError(f"Unsupported action: {action}")

    def ai_query(self, prompt: str) -> Any:
        """
        Query information from the screen using AI analysis.

        Args:
            prompt (str): Natural language query about the screen content.
                         Can include format hints like 'string[]' or 'number'.

        Returns:
            Any: The query results in the requested format

        Raises:
            ValueError: If the AI response cannot be parsed into the requested format
        """
        logger.info(f"🪽 AI Query: {prompt}")
        context = self._get_page_context()

        # Parse the requested data format
        format_hint = ""
        if prompt.startswith(('string[]', 'number[]', 'object[]')):
            format_hint = prompt.split(',')[0].strip()
            prompt = ','.join(prompt.split(',')[1:]).strip()

        # Provide different prompts based on the format
        if format_hint == 'string[]':
            query_prompt = f"""
Extract text content matching the query. Return ONLY a JSON array of strings.

Activity: {context['activity']}
Package: {context['package']}
Elements: {context['elements']}
Query: {prompt}

Return format example: ["result1", "result2"], (notice: Gets value data from labels and text keys)
No other text or explanation.
"""
        elif format_hint == 'number[]':
            query_prompt = f"""
Extract numeric values matching the query. Return ONLY a JSON array of numbers.

Activity: {context['activity']}
Package: {context['package']}
Elements: {context['elements']}
Query: {prompt}

Return format example: [1, 2, 3], (notice: Gets value data from labels and text keys)
No other text or explanation.
"""
        else:
            query_prompt = f"""
Extract information matching the query. Return ONLY in valid JSON format.

Activity: {context['activity']}
Package: {context['package']}
Elements: {context['elements']}
Query: {prompt}

Return format:
- For arrays: ["item1", "item2"]
- For objects: {{"key": "value"}}
- For single value: "text" or number
(notice: Gets value data from labels and text keys)

No other text or explanation.
"""

        response = self.llm_client.complete(query_prompt)
        cleaned_response = self._clean_response(response)
        try:
            result = json.loads(cleaned_response)
            query_info = self._validate_result_format(result, format_hint)
            logger.debug(f"📄 Query: {query_info}")
            return query_info
        except json.JSONDecodeError:
            # If it's a string array format, try extracting from text
            if format_hint == 'string[]':
                lines = [line.strip() for line in cleaned_response.split('\n')
                         if line.strip() and not line.startswith(('-', '*', '#'))]

                query_terms = [term.lower() for term in prompt.split()
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
                    seen = set()
                    query_info = [x for x in results if not (x in seen or seen.add(x))]
                    logger.debug(f"📄 Query: {query_info}")
                    return query_info

            raise ValueError(f"Failed to parse response as JSON: {cleaned_response[:100]}...")

    def ai_assert(self, prompt: str) -> bool:
        """
        Verify a condition on the screen using AI analysis.

        Args:
            prompt (str): Natural language description of the condition to verify

        Returns:
            bool: True if the condition is met, False otherwise

        Raises:
            ValueError: If the AI response cannot be parsed as a boolean value
        """
        logger.info(f"🪽 AI Assert: {prompt}")
        context = self._get_page_context()

        assert_prompt = f"""
You are a web automation assistant. Verify the following assertion and return ONLY a boolean value.

Activity: {context['activity']}
Package: {context['package']}
Elements: {context['elements']}
Assertion: {prompt}

(notice: Gets value data from labels and text keys)

IMPORTANT: Return ONLY the word 'true' or 'false' (lowercase). No other text, no explanation.
"""

        response = self.llm_client.complete(assert_prompt)
        cleaned_response = self._clean_response(response).lower()

        # Directly match true or false
        if cleaned_response == 'true':
            return True
        if cleaned_response == 'false':
            return False

        # If response contains other content, try extracting boolean
        if 'true' in cleaned_response.split():
            return True
        if 'false' in cleaned_response.split():
            return False

        raise ValueError("Response must be 'true' or 'false'")


def create_fixture():
    """
    Create an AppiumAiFixture factory.
    """
    return AppiumAiFixture
