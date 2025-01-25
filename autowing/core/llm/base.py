from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseLLMClient(ABC):

    @abstractmethod
    def complete(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        pass

    @abstractmethod
    def complete_with_vision(self, prompt: Dict[str, Any]) -> str:
        """Support vision analysis"""
        pass

    @classmethod
    def get_model_name(cls) -> str:
        return cls.__name__.lower().replace('client', '')
