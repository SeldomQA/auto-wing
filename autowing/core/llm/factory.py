from typing import Type
from autowing.core.llm.base import BaseLLMClient
from autowing.core.llm.openai_client import OpenAIClient
from autowing.core.llm.qwen_client import QwenClient


class LLMFactory:

    _models = {
        'openai': OpenAIClient,
        'qwen': QwenClient,
    }
    
    @classmethod
    def create(cls, model: str = "qwen") -> BaseLLMClient:
        model_name = model
        
        if model_name not in cls._models:
            raise ValueError(f"Unsupported model provider: {model_name}")
            
        model_class = cls._models[model_name]
        return model_class()
    
    @classmethod
    def register_model(cls, name: str, model_class: Type[BaseLLMClient]) -> None:
        cls._models[name.lower()] = model_class 