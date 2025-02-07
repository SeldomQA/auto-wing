import os
from typing import Type
from autowing.core.llm.base import BaseLLMClient
from autowing.core.llm.openai_client import OpenAIClient
from autowing.core.llm.qwen_client import QwenClient
from autowing.core.llm.deepseek_client import DeepSeekClient
from autowing.core.llm.doubao_client import DoubaoClient


class LLMFactory:
    """
    Factory class for creating Language Model clients.
    Provides centralized management of different LLM implementations.
    """

    _models = {
        'openai': OpenAIClient,
        'qwen': QwenClient,
        'deepseek': DeepSeekClient,
        'doubao': DoubaoClient
    }

    @classmethod
    def create(cls) -> BaseLLMClient:
        """
        Create an instance of the configured LLM client.

        Returns:
            BaseLLMClient: An instance of the specified LLM client

        Raises:
            ValueError: If the specified model provider is not supported
        """
        model_name = os.getenv("AUTOWING_MODEL_PROVIDER", "deepseek").lower()
        if model_name not in cls._models:
            raise ValueError(f"Unsupported model provider: {model_name}")

        model_class = cls._models[model_name]
        return model_class()
    
    @classmethod
    def register_model(cls, name: str, model_class: Type[BaseLLMClient]) -> None:
        """
        Register a new LLM client implementation.

        Args:
            name (str): The name to register the model under
            model_class (Type[BaseLLMClient]): The class implementing the BaseLLMClient interface
        """
        cls._models[name.lower()] = model_class 