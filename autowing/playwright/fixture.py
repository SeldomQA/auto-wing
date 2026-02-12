import json
from typing import Any, Dict

from loguru import logger
from playwright.sync_api import Page

from autowing.core.ai_fixture_web import AiFixtureWeb
from autowing.core.llm.factory import LLMFactory
from autowing.utils.transition import selector_to_locator


class PlaywrightAiFixture(AiFixtureWeb):
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
        super().__init__()
        self.page = page
        self.llm_client = LLMFactory.create()

    def _execute_marker_injection_script(self) -> Any:
        """Execute the JavaScript marker injection script for Playwright."""
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
            
            selectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(element => {
                    // Skip already marked elements
                    if (element.hasAttribute('data-autowing-id')) {
                        return;
                    }
                    
                    // Generate unique ID
                    const uniqueId = generateUniqueId();
                    element.setAttribute('data-autowing-id', uniqueId);
                    
                    // Collect element information
                    markers.push({
                        id: uniqueId,
                        tagName: element.tagName.toLowerCase(),
                        type: element.getAttribute('type') || null,
                        placeholder: element.getAttribute('placeholder') || null,
                        value: element.value || null,
                        textContent: element.textContent?.trim().substring(0, 100) || '',
                        ariaLabel: element.getAttribute('aria-label') || null,
                        role: element.getAttribute('role') || null,
                        boundingBox: element.getBoundingClientRect()
                    });
                });
            });
            
            return markers;
        })();
        """
        return self.page.evaluate(marker_script)

    def _get_basic_page_info(self) -> Dict[str, str]:
        """Get basic page information for Playwright."""
        return {
            "url": self.page.url,
            "title": self.page.title()
        }

    def _execute_elements_script(self) -> Any:
        """Execute JavaScript to get page elements information for Playwright."""
        return self.page.evaluate("""() => {
            const getVisibleElements = () => {
                const elements = [];
                const selectors = [
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
                
                for (const selector of selectors) {
                    document.querySelectorAll(selector).forEach(el => {
                        if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                            elements.push({
                                tag: el.tagName.toLowerCase(),
                                type: el.getAttribute('type') || null,
                                placeholder: el.getAttribute('placeholder') || null,
                                value: el.value || null,
                                text: el.textContent?.trim() || '',
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
                }
                return elements;
            };
            return getVisibleElements();
        }""")

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
        return """
            document.querySelectorAll('[data-autowing-id]').forEach(el => {
                el.removeAttribute('data-autowing-id');
            });
        """

    def _execute_javascript(self, script: str) -> Any:
        """Execute JavaScript code for Playwright."""
        return self.page.evaluate(script)

    def ai_action(self, prompt: str, iframe=None) -> None:
        """
        Execute an AI-driven action on the page based on the given prompt.
        The AI will analyze the page context and perform the requested action.

        Args:
            prompt (str): Natural language description of the action to perform
            iframe: FrameLocator object

        Raises:
            ValueError: If the AI response cannot be parsed or contains invalid instructions
            Exception: If the requested action cannot be performed
        """
        logger.info(f"🪽 AI Action: {prompt}")
        context = self._get_page_context()
        context["elements"] = self._remove_empty_keys(context.get("elements", []))

        def compute_action():
            action_prompt = f"""
You are a web automation assistant. Based on the following page context, provide instructions for the requested action.

Current page context:
URL: {context['url']}
Title: {context['title']}

Available elements with unique markers:
{json.dumps(context['elements'], indent=2)}

Element markers mapping (use these IDs for precise targeting):
{json.dumps(list(self._element_markers.values()), indent=2, default=str)}

User request: {prompt}

Return ONLY a JSON object with the following structure, no other text:
{{
    "selector": "CSS selector or XPath to locate the element",
    "action": "fill",
    "value": "text to input",
    "key": "key to press if needed",
    "markerId": "autowing marker ID if available for precise targeting"
}}
Note: 
- Prefer using markerId for precise element targeting when available
- selector is used for a playwright location, for example：page.locator(selector)
- If markerId is provided, use it instead of selector for better accuracy

Example response:
{{
    "selector": "//input[id='search-input']",
    "action": "fill",
    "value": "search text",
    "key": "Enter",
    "markerId": "aw-abc123def"
}}
            """
            response = self.llm_client.complete(action_prompt)
            cleaned_response = self._clean_response(response)
            return json.loads(cleaned_response)

        # Use cache manager to get or compute the instruction
        instruction = self._get_cached_or_compute(prompt, context, compute_action)
        
        # Execute action, prioritize using marker ID
        marker_id = instruction.get('markerId')
        selector = instruction.get('selector')
        action = instruction.get('action')

        if not action:
            raise ValueError("Invalid instruction format")

        # Prioritize using marker ID for precise targeting
        if marker_id and marker_id in self._element_markers:
            logger.debug(f"🎯 Using marker ID to locate element: {marker_id}")
            element = self._find_element_by_marker(marker_id)
        elif selector:
            selector = selector_to_locator(selector)
            element = self.page.locator(selector)
            if iframe is not None:
                element = iframe.locator(selector)
        else:
            raise ValueError("No valid selector or marker ID provided")

        # Execute specific action
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

        logger.info(f"✅ Action executed: {action}")

    def ai_query(self, prompt: str) -> Any:
        """
        Query information from the page using AI analysis.
        Supports various data formats including arrays, objects, and primitive types.

        Args:
            prompt (str): Natural language query about the page content.
                         It can include format hints like 'string[]' or 'number'.

        Returns:
            Any: The query results in the requested format

        Raises:
            ValueError: If the AI response cannot be parsed into the requested format
        """
        logger.info(f"🪽 AI Query: {prompt}")
        context = self._get_page_context()
        context["elements"] = self._remove_empty_keys(context.get("elements", []))

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
        context["elements"] = self._remove_empty_keys(context.get("elements", []))

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

            # If responses contain other content, try extracting boolean
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
