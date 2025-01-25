from typing import Any, Dict, Optional
import json


class AiContext:
    """
    A class for managing AI context data.
    Provides storage and retrieval of context information used in AI operations.
    """

    def __init__(self):
        """
        Initialize an empty context storage.
        """
        self._context: Dict[str, Any] = {}
        
    def set_context(self, key: str, value: Any) -> None:
        """
        Store a value in the context.

        Args:
            key (str): The key under which to store the value
            value (Any): The value to store
        """
        self._context[key] = value

    def get_context(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the context.

        Args:
            key (str): The key of the value to retrieve

        Returns:
            Optional[Any]: The stored value, or None if the key doesn't exist
        """
        return self._context.get(key)

    def to_json(self) -> str:
        """
        Convert the context to a JSON string.

        Returns:
            str: JSON string representation of the context
        """
        return json.dumps(self._context)
