from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseLLMClient(ABC):
    """
    Abstract base class for Language Model clients.
    Defines the interface that all LLM clients must implement.
    """

    @abstractmethod
    def complete(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a completion for the given prompt with optional context.

        Args:
            prompt (str): The input text to generate completion for
            context (Optional[Dict[str, Any]]): Additional context information for the completion

        Returns:
            str: The generated completion text

        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        pass

    @abstractmethod
    def complete_with_vision(self, prompt: Dict[str, Any]) -> str:
        """
        Generate a completion for vision-based tasks.

        Args:
            prompt (Dict[str, Any]): A dictionary containing the prompt and image data
                                   in the format required by the specific model

        Returns:
            str: The generated completion text

        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        pass

    @classmethod
    def get_model_name(cls) -> str:
        """
        Get the standardized name of the model.

        Returns:
            str: The model name in lowercase, with 'client' suffix removed
        """
        return cls.__name__.lower().replace('client', '')
