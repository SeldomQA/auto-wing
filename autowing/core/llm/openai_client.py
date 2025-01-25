import os
from typing import Optional, Dict, Any
from openai import OpenAI
from autowing.core.llm.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """
    OpenAI API client implementation.
    Provides access to OpenAI's GPT and vision models.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the OpenAI client.

        Args:
            api_key (Optional[str]): OpenAI API key. If not provided, will try to get from OPENAI_API_KEY env var
            base_url (Optional[str]): Custom base URL for API requests

        Raises:
            ValueError: If no API key is provided or found in environment variables
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
            
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model_name = os.getenv("MIDSCENE_MODEL_NAME", "gpt-4-vision-preview")
        
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
            
        self.client = OpenAI(**client_kwargs)
        
    def complete(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a completion using GPT-4.

        Args:
            prompt (str): The text prompt to complete
            context (Optional[Dict[str, Any]]): Additional context for the completion

        Returns:
            str: The model's response text

        Raises:
            Exception: If there's an error communicating with the OpenAI API
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant for web automation."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
            
    def complete_with_vision(self, prompt: Dict[str, Any]) -> str:
        """
        Generate a completion for vision tasks using GPT-4 Vision.

        Args:
            prompt (Dict[str, Any]): A dictionary containing messages and image data
                                   in the format required by the GPT-4 Vision API

        Returns:
            str: The model's response text

        Raises:
            Exception: If there's an error communicating with the OpenAI Vision API
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=prompt["messages"],
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI Vision API error: {str(e)}")
