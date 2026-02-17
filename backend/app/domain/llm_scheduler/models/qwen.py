from typing import List, Optional, AsyncGenerator
import httpx

from app.domain.llm_scheduler.base import BaseLLM, ChatMessage, ChatResponse, MessageRole


class QwenLLM(BaseLLM):
    """Qwen大模型实现"""

    name = "qwen"
    default_model = "qwen-pro-32k"
    supported_models = [
        "qwen-pro-32k",
        "qwen-pro-128k",
        "qwen-lite-32k",
        "qwen-lite-128k"
    ]

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key, base_url, model)
        self.base_url = base_url or "https://ark.cn-beijing.volces.com/api/v3"

    def _convert_messages(self, messages: List[ChatMessage]) -> List[dict]:
        converted = []
        for msg in messages:
            converted_msg = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                converted_msg["name"] = msg.name
            converted.append(converted_msg)
        return converted

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs
    ) -> ChatResponse:
        payload = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        return ChatResponse(
            content=choice["message"]["content"],
            model=self.model,
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason"),
            raw_response=data
        )

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "top_p": top_p,
            "stream": True
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            import json
                            data = json.loads(data_str)
                            if data["choices"]:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except Exception:
                            continue
