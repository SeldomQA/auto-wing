from typing import Any, Dict, Optional
import json


class AiContext:

    def __init__(self):
        self._context: Dict[str, Any] = {}
        
    def set_context(self, key: str, value: Any) -> None:
        self._context[key] = value

    def get_context(self, key: str) -> Optional[Any]:
        return self._context.get(key)

    def to_json(self) -> str:
        return json.dumps(self._context)
