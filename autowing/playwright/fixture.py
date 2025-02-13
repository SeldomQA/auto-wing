from typing import Any, Dict
import json
from playwright.sync_api import Page
from autowing.core.llm.factory import LLMFactory
from autowing.core.ai_fixture_base import AiFixtureBase
from loguru import logger


class PlaywrightAiFixture(AiFixtureBase):
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
        # Get basic page info
        basic_info = {
            "url": self.page.url,
            "title": self.page.title()
        }
        
        # Get key elements info
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
        logger.info(f"🪽 AI Action: {prompt}")
        context = self._get_page_context()
        
        # Construct the prompt, explicitly requiring a JSON response
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
        cleaned_response = self._clean_response(response)
        try:
            instruction = json.loads(cleaned_response)
            selector = instruction.get('selector')
            action = instruction.get('action')
            
            if not selector or not action:
                raise ValueError("Invalid instruction format")
                
            # Perform the action
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
            raise ValueError(f"Failed to parse instruction: {cleaned_response}")
            
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
            # Default prompt
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

        response = self.llm_client.complete(query_prompt)
        cleaned_response = self._clean_response(response)
        try:
            cleaned_response = self._clean_response(response)
            try:
                result = json.loads(cleaned_response)
                query_info = self._validate_result_format(result, format_hint)
                logger.debug(f"📄 Query: {query_info}")
                return query_info
            except json.JSONDecodeError:
                # If it's a string array format, try extracting from text
                if format_hint == 'string[]':
                    # Split and clean text
                    lines = [line.strip() for line in cleaned_response.split('\n') 
                            if line.strip() and not line.startswith(('-', '*', '#'))]
                    
                    # Extract lines containing query terms
                    query_terms = [term.lower() for term in prompt.split() 
                                 if len(term) > 2 and term.lower() not in ['the', 'and', 'for']]
                    
                    results = []
                    for line in lines:
                        # Check if line contains query terms
                        if any(term in line.lower() for term in query_terms):
                            # Clean text
                            text = line.strip('`"\'- ,')
                            if ':' in text:
                                text = text.split(':', 1)[1].strip()
                            if text:
                                results.append(text)
                    
                    if results:
                        # Remove duplicates while preserving order
                        seen = set()
                        query_info = [x for x in results if not (x in seen or seen.add(x))]
                        logger.debug(f"📄 Query: {query_info}")
                        return query_info
                
                raise ValueError(f"Failed to parse response as JSON: {cleaned_response[:100]}...")
            
        except Exception as e:
            raise ValueError(f"Query failed. Error: {str(e)}\nResponse: {cleaned_response[:100]}...")

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
        logger.info(f"🪽 AI Assert: {prompt}")
        context = self._get_page_context()
        
        # Optimize the prompt to be concise and explicitly require a boolean return
        assert_prompt = f"""
You are a web automation assistant. Verify the following assertion and return ONLY a boolean value.

Page URL: {context['url']}
Page Title: {context['title']}

Assertion: {prompt}

IMPORTANT: Return ONLY the word 'true' or 'false' (lowercase). No other text, no explanation.
"""
        
        response = self.llm_client.complete(assert_prompt)
        cleaned_response = self._clean_response(response).lower()
        
        try:
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
            
        except Exception as e:
            # Provide more useful error information
            raise ValueError(
                f"Failed to parse assertion result. Response: {cleaned_response[:100]}... "
                f"Error: {str(e)}"
            )

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

        try:
            response = self.llm_client.complete(case_prompt)
            cleaned_response = self._clean_response(response)

            logger.debug(f"""📄 Function Cases:\n {cleaned_response}""")
            return cleaned_response
        except Exception as e:
            raise ValueError(f"Failed to generate test cases. Error: {str(e)}\nResponse: {cleaned_response[:100]}...")


def create_fixture():
    """
    Create a PlaywrightAiFixture factory.

    Returns:
        Callable[[Page], PlaywrightAiFixture]: A factory function that creates
        PlaywrightAiFixture instances
    """
    return PlaywrightAiFixture
