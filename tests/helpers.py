"""Shared test doubles for LLM mocking (plan item T4).

FakeLLMClient implements the BaseLLMClient interface with scripted
responses so every layer (factory, fixtures, action loops) can be tested
offline - no API key, no network, no real model.
"""
from typing import Any, Dict, List, Optional

from autowing.core.llm.base import BaseLLMClient


class FakeLLMClient(BaseLLMClient):
    """
    Scriptable stand-in for a real LLM client.

    Responses are consumed in FIFO order; when the queue is empty the last
    response is repeated (useful for retry loops). Every call is recorded
    in self.prompts / self.vision_payloads for assertions.
    """

    def __init__(self, responses: Optional[List[str]] = None):
        self.responses = list(responses or [])
        self.prompts: List[str] = []
        self.vision_payloads: List[Dict[str, Any]] = []

    def complete(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        self.prompts.append(prompt)
        if len(self.prompts) <= len(self.responses):
            return self.responses[len(self.prompts) - 1]
        if self.responses:
            return self.responses[-1]
        raise AssertionError("FakeLLMClient received an unexpected extra call")

    def complete_with_vision(self, prompt: Dict[str, Any]) -> str:
        self.vision_payloads.append(prompt)
        return self.complete("<<vision>>")
