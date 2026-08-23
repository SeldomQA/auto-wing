import json
import re
from typing import Any, Dict, Optional

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from loguru import logger
from selenium.webdriver.support.ui import WebDriverWait

from autowing.appium.actions import Action
from autowing.core.ai_fixture_base import AiFixtureBase
from autowing.core.llm.factory import LLMFactory


def bounds(x, y, width, height) -> list:
    """
    return element bounds
    :param x:
    :param y:
    :param width:
    :param height:
    :return:
    """
    x_start = int(x)
    y_start = int(y)
    x_end = x_start + int(width)
    y_end = y_start + int(height)
    return [[x_start, x_end], [y_start, y_end]]


class AppiumAiFixture(AiFixtureBase):
    """
    A fixture class that combines Appium with AI capabilities for mobile automation.
    Provides AI-driven interaction with mobile apps using various LLM providers.
    """

    def __init__(self, driver: WebDriver, platform: str = "Android"):
        """
        Initialize the AI-powered Appium fixture.

        Args:
            driver (WebDriver): The Appium WebDriver instance to automate
            platform: Mobile operating system platform
        """
        super().__init__()
        self.driver = driver
        self.platform = platform
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
        if self.platform == "Android":
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
        elif self.platform == "iOS":
            elements = self.driver.find_elements(AppiumBy.IOS_PREDICATE, "type == '*'")
            for el in elements:
                if el.is_displayed():
                    elements_info.append({
                        "tag": el.tag_name,
                        "text": el.text,
                        "type": el.get_attribute("type"),
                        "name": el.get_attribute("name"),
                        "label": el.get_attribute("label"),
                        "enabled": el.get_attribute("enabled"),
                        "visible": el.get_attribute("visible"),
                        "bounds": bounds(el.get_attribute("x"),
                                         el.get_attribute("y"),
                                         el.get_attribute("width"),
                                         el.get_attribute("height")),
                    })
        else:
            raise NameError(f"Unsupported {self.platform} platform.")

        return {
            **basic_info,
            "elements": elements_info
        }

    def _capture_screenshot_base64(self) -> Optional[str]:
        """Capture the current screen as a base64-encoded PNG image."""
        return self.driver.get_screenshot_as_base64()

    def _llm_prompt_notice(self) -> str:
        """Appium-specific hint: element values live in label/text keys."""
        return "(notice: Gets value data from labels and text keys)"

    def ai_action(self, prompt: str) -> None:
        """
        Execute an AI-driven action on the screen based on the given prompt.

        Failed attempts trigger a re-plan: the LLM is called again with the
        error as extra context (up to AUTOWING_MAX_RETRIES, default 2).

        Args:
            prompt (str): Natural language description of the action to perform

        Raises:
            ValueError: If the AI response cannot be parsed or contains invalid instructions
            TimeoutException: If the element cannot be found or interacted with
        """
        logger.info(f"🪽 AI Action: {prompt}")
        context = self._get_page_context()

        def validate_instruction(instruction):
            if isinstance(instruction, list) is False:
                raise ValueError("Invalid instruction format")
            return instruction

        def compute_action(error_hint: str = "") -> list:
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
            if error_hint:
                action_prompt += f"""
NOTICE: A previous attempt on this screen failed with: {error_hint}
Re-plan carefully to avoid the same problem.
"""
            return self._llm_json_with_retry(action_prompt, validate_instruction)

        instruction = compute_action()
        total_attempts = self._max_action_retries + 1
        last_error = None
        for attempt in range(total_attempts):
            try:
                self._execute_action_instruction(instruction)
                return
            except Exception as e:
                last_error = e
                if attempt >= self._max_action_retries:
                    break
                logger.warning(f"⚠️ Action attempt {attempt + 1}/{total_attempts} failed: {e}. "
                               f"Re-planning with error context...")
                instruction = compute_action(str(e))
        logger.error(f"❌ ai_action failed after {total_attempts} attempts: {last_error}")
        raise last_error

    def _execute_action_instruction(self, instruction: list) -> None:
        """
        Execute parsed ai_action steps on the screen.

        Args:
            instruction (list): Parsed LLM steps (bounds/action/value/key)

        Raises:
            ValueError: If a step is invalid or contains an unsupported action
        """
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



def create_fixture():
    """
    Create an AppiumAiFixture factory.
    """
    return AppiumAiFixture
