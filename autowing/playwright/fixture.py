from typing import Any, Dict
import json
from playwright.sync_api import Page
from autowing.core.llm.factory import LLMFactory


class PlaywrightAiFixture:
    """
    A fixture class that combines Playwright with AI capabilities for web automation.
    Provides AI-driven interaction with web pages using various LLM providers.
    """

    def __init__(self, page: Page):
        """
        Initialize the AI-powered Playwright fixture.

        Args:
            page (Page): The Playwright page object to automate
        """
        self.page = page
        self.llm_client = LLMFactory.create()

    def _get_page_context(self) -> Dict[str, Any]:
        """
        Extract context information from the current page.
        Collects information about visible elements and page metadata.

        Returns:
            Dict[str, Any]: A dictionary containing page URL, title, and information about
                           visible interactive elements
        """
        # 获取页面基本信息
        basic_info = {
            "url": self.page.url,
            "title": self.page.title()
        }
        
        # 获取关键元素信息
        elements_info = self.page.evaluate("""() => {
            const getVisibleElements = () => {
                const elements = [];
                const selectors = [
                    'input', 'button', 'a', '[role="button"]',
                    '[role="link"]', '[role="searchbox"]', 'textarea'
                ];
                
                for (const selector of selectors) {
                    document.querySelectorAll(selector).forEach(el => {
                        if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                            elements.push({
                                tag: el.tagName.toLowerCase(),
                                type: el.getAttribute('type'),
                                placeholder: el.getAttribute('placeholder'),
                                value: el.value,
                                text: el.textContent?.trim(),
                                aria: el.getAttribute('aria-label'),
                                id: el.id,
                                name: el.getAttribute('name'),
                                class: el.className
                            });
                        }
                    });
                }
                return elements;
            };
            return getVisibleElements();
        }""")
        
        return {
            **basic_info,
            "elements": elements_info
        }
        
    def ai_action(self, prompt: str) -> None:
        """
        Execute an AI-driven action on the page based on the given prompt.
        The AI will analyze the page context and perform the requested action.

        Args:
            prompt (str): Natural language description of the action to perform

        Raises:
            ValueError: If the AI response cannot be parsed or contains invalid instructions
            Exception: If the requested action cannot be performed
        """
        context = self._get_page_context()
        
        # 构建提示，明确要求JSON格式的响应
        action_prompt = f"""
You are a web automation assistant. Based on the following page context, provide instructions for the requested action.

Current page context:
URL: {context['url']}
Title: {context['title']}

Available elements:
{json.dumps(context['elements'], indent=2)}

User request: {prompt}

Return ONLY a JSON object with the following structure, no other text:
{{
    "selector": "CSS selector or XPath to locate the element",
    "action": "fill",
    "value": "text to input",
    "key": "key to press if needed"
}}

Example response:
{{
    "selector": "#search-input",
    "action": "fill",
    "value": "search text",
    "key": "Enter"
}}
"""
        
        response = self.llm_client.complete(action_prompt)
        
        try:
            # 尝试提取JSON部分
            json_str = response
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
                
            instruction = json.loads(json_str)
            selector = instruction.get('selector')
            action = instruction.get('action')
            
            if not selector or not action:
                raise ValueError("Invalid instruction format")
                
            # 执行操作
            element = self.page.locator(selector)
            if action == 'click':
                element.click()
            elif action == 'fill':
                element.fill(instruction.get('value', ''))
                if instruction.get('key'):
                    element.press(instruction.get('key'))
            elif action == 'press':
                element.press(instruction.get('key', 'Enter'))
            else:
                raise ValueError(f"Unsupported action: {action}")
                
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse instruction: {response}")
            
    def ai_query(self, prompt: str) -> Any:
        """
        Query information from the page using AI analysis.

        Args:
            prompt (str): Natural language query about the page content

        Returns:
            Any: The query results as parsed from the AI response

        Raises:
            ValueError: If the AI response cannot be parsed into valid JSON
        """
        context = self._get_page_context()
        
        query_prompt = f"""
You are a web automation assistant. Based on the following page context, answer the query.

Current page context:
URL: {context['url']}
Title: {context['title']}

Available elements:
{json.dumps(context['elements'], indent=2)}

Query: {prompt}

Return ONLY a JSON array of results, no other text.
"""
        
        response = self.llm_client.complete(query_prompt)
        
        try:
            # 尝试提取JSON部分
            json_str = response
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
                
            return json.loads(json_str)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse query results: {response}")
            
    def ai_assert(self, prompt: str) -> bool:
        """
        Verify a condition on the page using AI analysis.

        Args:
            prompt (str): Natural language description of the condition to verify

        Returns:
            bool: True if the condition is met, False otherwise

        Raises:
            ValueError: If the AI response cannot be parsed as a boolean value
        """
        context = self._get_page_context()
        
        assert_prompt = f"""
You are a web automation assistant. Based on the following page context, verify the assertion.

Current page context:
URL: {context['url']}
Title: {context['title']}

Available elements:
{json.dumps(context['elements'], indent=2)}

Assertion to verify: {prompt}

Return ONLY true or false as a JSON boolean, no other text.
Example: true
"""
        
        response = self.llm_client.complete(assert_prompt)
        
        try:
            # 尝试提取JSON部分
            json_str = response.lower().strip()
            if 'true' in json_str:
                return True
            if 'false' in json_str:
                return False
            raise ValueError("Invalid assertion response")
        except Exception:
            raise ValueError(f"Failed to parse assertion result: {response}")


def create_fixture():
    """
    Create a PlaywrightAiFixture factory.

    Returns:
        Callable[[Page], PlaywrightAiFixture]: A factory function that creates
        PlaywrightAiFixture instances
    """
    return PlaywrightAiFixture
