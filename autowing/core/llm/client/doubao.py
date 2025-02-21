import json
import os
from typing import Optional, Dict, Any, List

from openai import OpenAI

from autowing.core.llm.base import BaseLLMClient


class DoubaoClient(BaseLLMClient):
    """
    Doubao API client implementation.
    Provides access to Doubao's LLM models.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the Doubao client.

        Args:
            api_key (Optional[str]): Doubao API key. If not provided, will try to get from ARK_API_KEY env var
            base_url (Optional[str]): Custom base URL for API requests

        Raises:
            ValueError: If no API key is provided or found in environment variables
        """
        self.api_key = api_key or os.getenv("ARK_API_KEY")
        if not self.api_key:
            raise ValueError("Doubao API key is required")

        self.base_url = base_url or os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        self.model_name = os.getenv("DOUBAO_MODEL_NAME")
        if not self.model_name:
            raise ValueError("Doubao model name is null, For example: ep-20250207200649-xxx")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _truncate_text(self, text: str, max_length: int = 30000) -> str:
        """
        Truncate text to fit within model's length limits.

        Args:
            text (str): The input text to truncate
            max_length (int): Maximum allowed length for the text. Defaults to 30000

        Returns:
            str: Truncated text with ellipsis if needed
        """
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text

    def _format_messages(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """
        Format messages for the Doubao API.

        Args:
            prompt (str): The main prompt text
            context (Optional[Dict[str, Any]]): Additional context information

        Returns:
            List[Dict[str, str]]: Formatted messages list ready for API submission
        """
        # Add system message
        messages = [{
            "role": "system",
            "content": (
                "You are a web automation assistant. "
                "Analyze the page structure and provide precise element locators. "
                "Return responses in the requested format."
            )
        }]

        # Add context (if any)
        if context:
            context_str = json.dumps(context, ensure_ascii=False)
            messages.append({
                "role": "user",
                "content": f"Page context: {self._truncate_text(context_str)}"
            })

        # Add main prompt
        messages.append({
            "role": "user",
            "content": self._truncate_text(prompt)
        })

        return messages

    def complete(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a completion using Doubao LLM.

        Args:
            prompt (str): The text prompt to complete
            context (Optional[Dict[str, Any]]): Additional context for the completion

        Returns:
            str: The model's response text

        Raises:
            Exception: If there's an error communicating with the Doubao API
        """
        try:
            messages = self._format_messages(prompt, context)

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Doubao API error: {str(e)}")

    def complete_with_vision(self, prompt: Dict[str, Any]) -> str:
        """
        Generate a completion for vision tasks using Doubao Vision.

        Args:
            prompt (Dict[str, Any]): A dictionary containing messages and image data
                                   in the format required by the Doubao Vision API

        Returns:
            str: The model's response text

        Raises:
            Exception: If there's an error communicating with the Doubao Vision API
        """
        try:
            # Make sure the message length is within the limit
            messages = prompt["messages"]
            for msg in messages:
                if isinstance(msg.get("content"), str):
                    msg["content"] = self._truncate_text(msg["content"])
                elif isinstance(msg.get("content"), list):
                    for item in msg["content"]:
                        if isinstance(item.get("text"), str):
                            item["text"] = self._truncate_text(item["text"])

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Doubao Vision API error: {str(e)}")
