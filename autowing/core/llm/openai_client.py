import os
from typing import Optional, Dict, Any
from openai import OpenAI
from autowing.core.llm.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
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
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=prompt["messages"],
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI Vision API error: {str(e)}")
