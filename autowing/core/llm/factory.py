import os
from typing import Type

from loguru import logger

from autowing.core.llm.base import BaseLLMClient
from autowing.core.llm.client.deepseek import DeepSeekClient
from autowing.core.llm.client.doubao import DoubaoClient
from autowing.core.llm.client.openai import OpenAIClient
from autowing.core.llm.client.qwen import QwenClient


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

        logger.info(f"🤖 AUTOWING_MODEL_PROVIDER={model_name}")

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
