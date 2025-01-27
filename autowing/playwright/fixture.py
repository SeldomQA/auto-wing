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
        Supports various data formats including arrays, objects, and primitive types.

        Args:
            prompt (str): Natural language query about the page content.
                         Can include format hints like 'string[]' or 'number'.

        Returns:
            Any: The query results in the requested format

        Raises:
            ValueError: If the AI response cannot be parsed into the requested format
        """
        context = self._get_page_context()
        
        # 解析请求的数据格式
        format_hint = ""
        if prompt.startswith(('string[]', 'number[]', 'object[]')):
            format_hint = prompt.split(',')[0].strip()
            prompt = ','.join(prompt.split(',')[1:]).strip()

        # 根据不同的格式提供不同的提示
        if format_hint == 'string[]':
            query_prompt = f"""
Extract text content matching the query. Return ONLY a JSON array of strings.

Page: {context['url']}
Title: {context['title']}
Query: {prompt}

Return format example: ["result1", "result2"]
No other text or explanation.
"""
        elif format_hint == 'number[]':
            query_prompt = f"""
Extract numeric values matching the query. Return ONLY a JSON array of numbers.

Page: {context['url']}
Title: {context['title']}
Query: {prompt}

Return format example: [1, 2, 3]
No other text or explanation.
"""
        else:
            # 默认提示
            query_prompt = f"""
Extract information matching the query. Return ONLY in valid JSON format.

Page: {context['url']}
Title: {context['title']}
Query: {prompt}

Return format:
- For arrays: ["item1", "item2"]
- For objects: {{"key": "value"}}
- For single value: "text" or number

No other text or explanation.
"""

        try:
            response = self.llm_client.complete(query_prompt)
            
            # 清理响应
            response = response.strip()
            
            # 移除可能的markdown格式
            if '```' in response:
                response = response.split('```')[1].split('```')[0].strip()
                if response.startswith(('json', 'python')):
                    response = response.split('\n', 1)[1]
            
            # 尝试解析JSON
            try:
                result = json.loads(response)
                return self._validate_result_format(result, format_hint)
            except json.JSONDecodeError:
                # 如果是字符串数组格式，尝试从文本中提取
                if format_hint == 'string[]':
                    # 分割文本并清理
                    lines = [line.strip() for line in response.split('\n') 
                            if line.strip() and not line.startswith(('-', '*', '#'))]
                    
                    # 提取包含查询关键词的行
                    query_terms = [term.lower() for term in prompt.split() 
                                 if len(term) > 2 and term.lower() not in ['the', 'and', 'for']]
                    
                    results = []
                    for line in lines:
                        # 检查是否包含查询关键词
                        if any(term in line.lower() for term in query_terms):
                            # 清理文本
                            text = line.strip('`"\'- ,')
                            if ':' in text:
                                text = text.split(':', 1)[1].strip()
                            if text:
                                results.append(text)
                    
                    if results:
                        # 去重并保持顺序
                        seen = set()
                        return [x for x in results if not (x in seen or seen.add(x))]
                
                raise ValueError(f"Failed to parse response as JSON: {response[:100]}...")
            
        except Exception as e:
            raise ValueError(f"Query failed. Error: {str(e)}\nResponse: {response[:100]}...")

    def _validate_result_format(self, result: Any, format_hint: str) -> Any:
        """
        Validate and convert the result to match the requested format.

        Args:
            result: The parsed result from AI response
            format_hint: The requested format (e.g., 'string[]')

        Returns:
            The validated and possibly converted result

        Raises:
            ValueError: If the result doesn't match the requested format
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
        
        # 优化提示，使其更简洁，更明确要求布尔值返回
        assert_prompt = f"""
You are a web automation assistant. Verify the following assertion and return ONLY a boolean value.

Page URL: {context['url']}
Page Title: {context['title']}

Assertion: {prompt}

IMPORTANT: Return ONLY the word 'true' or 'false' (lowercase). No other text, no explanation.
"""
        
        try:
            # 缓存相同的断言结果
            response = self.llm_client.complete(assert_prompt)
            
            # 简化响应处理
            response = response.lower().strip()
            
            # 移除可能的markdown格式
            response = response.replace('```', '').strip()
            
            # 直接匹配 true 或 false
            if response == 'true':
                return True
            if response == 'false':
                return False
            
            # 如果响应包含其他内容，尝试提取布尔值
            if 'true' in response.split():
                return True
            if 'false' in response.split():
                return False
            
            raise ValueError("Response must be 'true' or 'false'")
            
        except Exception as e:
            # 提供更有用的错误信息
            raise ValueError(
                f"Failed to parse assertion result. Response: {response[:100]}... "
                f"Error: {str(e)}"
            )


def create_fixture():
    """
    Create a PlaywrightAiFixture factory.

    Returns:
        Callable[[Page], PlaywrightAiFixture]: A factory function that creates
        PlaywrightAiFixture instances
    """
    return PlaywrightAiFixture
