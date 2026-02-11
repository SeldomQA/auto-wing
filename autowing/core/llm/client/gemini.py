import json
import os
from typing import Optional, Dict, Any, List

from google import genai
from google.genai import types

from autowing.core.llm.base import BaseLLMClient


class GeminiClient(BaseLLMClient):
    """
    Google Gemini API client implementation.
    Provides access to Google's Gemini models.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini client.

        Args:
            api_key (Optional[str]): Google Gemini API key. If not provided, will try to get from GOOGLE_API_KEY env var

        Raises:
            ValueError: If no API key is provided or found in environment variables
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google Gemini API key is required")

        self.model_name = os.getenv("MIDSCENE_MODEL_NAME", "gemini-2.0-flash")
        
        # Create client for Gemini Developer API
        self.client = genai.Client(api_key=self.api_key)

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

    def _format_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Format prompt for the Gemini API.

        Args:
            prompt (str): The main prompt text
            context (Optional[Dict[str, Any]]): Additional context information

        Returns:
            List[Dict[str, Any]]: Formatted contents list ready for API submission
        """
        parts = []
        
        # Add system-like instruction
        system_instruction = (
            "You are a web automation assistant. "
            "Analyze the page structure and provide precise element locators. "
            "Return responses in the requested format."
        )
        parts.append({"text": system_instruction})
        
        # Add context (if any)
        if context:
            context_str = json.dumps(context, ensure_ascii=False)
            parts.append({"text": f"Page context: {self._truncate_text(context_str)}"})

        # Add main prompt
        parts.append({"text": self._truncate_text(prompt)})
        
        return [{"parts": parts}]

    def complete(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a completion using Gemini.

        Args:
            prompt (str): The text prompt to complete
            context (Optional[Dict[str, Any]]): Additional context for the completion

        Returns:
            str: The model's response text

        Raises:
            Exception: If there's an error communicating with the Gemini API
        """
        try:
            formatted_contents = self._format_prompt(prompt, context)
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=formatted_contents,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=2000
                )
            )
            
            if response.text:
                return response.text
            else:
                raise Exception("Empty response from Gemini API")
                
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
        finally:
            # Close the client to release resources
            self.client.close()

    def complete_with_vision(self, prompt: Dict[str, Any]) -> str:
        """
        Generate a completion for vision tasks using Gemini.

        Args:
            prompt (Dict[str, Any]): A dictionary containing messages and image data
                                   in the format required by the Gemini Vision API

        Returns:
            str: The model's response text

        Raises:
            Exception: If there's an error communicating with the Gemini Vision API
        """
        try:
            # Extract content from the prompt structure
            messages = prompt.get("messages", [])
            parts = []
            
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str):
                    # Text content
                    parts.append({"text": self._truncate_text(content)})
                elif isinstance(content, list):
                    # Mixed content (text + images)
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                parts.append({"text": self._truncate_text(item.get("text", ""))})
                            elif item.get("type") == "image_url":
                                # Handle image URLs - Gemini expects image data differently
                                image_url = item.get("image_url", {}).get("url", "")
                                if image_url:
                                    # For simplicity, we'll treat this as text for now
                                    # In a full implementation, you'd need to download and process the image
                                    parts.append({"text": f"[Image: {image_url}]"})
            
            contents = [{"parts": parts}]
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=2000
                )
            )
            
            if response.text:
                return response.text
            else:
                raise Exception("Empty response from Gemini Vision API")
                
        except Exception as e:
            raise Exception(f"Gemini Vision API error: {str(e)}")
        finally:
            # Close the client to release resources
            self.client.close()
