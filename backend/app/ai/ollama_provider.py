from collections.abc import Sequence

import httpx

from app.ai.provider import LLMMessage, LLMProvider
from app.config import get_settings


class OllamaUnavailableError(RuntimeError):
    pass


class OllamaProvider(LLMProvider):
    @property
    def model(self) -> str:
        return get_settings().ollama_model

    @property
    def _base_url(self) -> str:
        return get_settings().ollama_base_url.rstrip("/")

    async def is_available(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
        except httpx.HTTPError:
            return False, "Não foi possível conectar ao Ollama local."
        model_names = {item.get("name") for item in models}
        if self.model not in model_names:
            return False, f"O Ollama está ativo, mas o modelo '{self.model}' não foi encontrado."
        return True, "Ollama e modelo local disponíveis."

    async def chat(self, messages: Sequence[LLMMessage]) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
            "messages": [{"role": item.role, "content": item.content} for item in messages],
        }
        try:
            async with httpx.AsyncClient(
                timeout=get_settings().ollama_timeout_seconds
            ) as client:
                response = await client.post(f"{self._base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as error:
            raise OllamaUnavailableError(
                "Não foi possível obter resposta do Ollama local."
            ) from error

        content = response.json().get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaUnavailableError("O Ollama retornou uma resposta vazia.")
        return content

