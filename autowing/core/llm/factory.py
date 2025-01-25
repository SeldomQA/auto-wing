import os
from typing import Type
from autowing.core.llm.base import BaseLLMClient
from autowing.core.llm.openai_client import OpenAIClient
from autowing.core.llm.qwen_client import QwenClient
from autowing.core.llm.deepseek_client import DeepSeekClient


class LLMFactory:

    _models = {
        'openai': OpenAIClient,
        'qwen': QwenClient,
        'deepseek': DeepSeekClient
    }

    @classmethod
    def create(cls) -> BaseLLMClient:
        model_name = os.getenv("AUTOWING_MODEL_PROVIDER", "qwen").lower()

        if model_name not in cls._models:
            raise ValueError(f"Unsupported model provider: {model_name}")

        model_class = cls._models[model_name]
        return model_class()
    
    @classmethod
    def register_model(cls, name: str, model_class: Type[BaseLLMClient]) -> None:
        cls._models[name.lower()] = model_class 