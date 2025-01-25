import os
import json
from typing import Optional, Dict, Any, List
from openai import OpenAI
from autowing.core.llm.base import BaseLLMClient


class QwenClient(BaseLLMClient):

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DashScope API key is required")

        # 使用兼容模式的 URL
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model_name = os.getenv("MIDSCENE_MODEL_NAME", "qwen-vl-max-latest")

        # 使用 OpenAI 客户端，但配置为千问的 URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def _truncate_text(self, text: str, max_length: int = 30000) -> str:
        """截断文本以适应模型限制"""
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text

    def _format_messages(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """格式化消息"""
        messages = []

        # 添加系统消息
        messages.append({
            "role": "system",
            "content": (
                "You are a web automation assistant. "
                "Analyze the page structure and provide precise element locators. "
                "Return responses in the requested format."
            )
        })

        # 添加上下文（如果有）
        if context:
            context_str = json.dumps(context, ensure_ascii=False)
            messages.append({
                "role": "user",
                "content": f"Page context: {self._truncate_text(context_str)}"
            })

        # 添加主要提示
        messages.append({
            "role": "user",
            "content": self._truncate_text(prompt)
        })

        return messages

    def complete(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        try:
            messages = self._format_messages(prompt, context)

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Qwen API error: {str(e)}")

    def complete_with_vision(self, prompt: Dict[str, Any]) -> str:
        try:
            # 确保消息长度在限制范围内
            messages = prompt["messages"]
            for msg in messages:
                if isinstance(msg.get("content"), str):
                    msg["content"] = self._truncate_text(msg["content"])
                elif isinstance(msg.get("content"), list):
                    for item in msg["content"]:
                        if isinstance(item.get("text"), str):
                            item["text"] = self._truncate_text(item["text"])

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Qwen API error: {str(e)}")