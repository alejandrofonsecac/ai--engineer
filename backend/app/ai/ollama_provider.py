from collections.abc import Sequence
import httpx
from app.ai.provider import (
    LLMMessage, LLMResponseError, LLMTimeoutError, LLMUnavailableError,
)
from app.config import Settings, get_settings


class OllamaProvider:
    def __init__(self, settings: Settings | None = None,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings or get_settings()
        self.transport = transport

    @property
    def model(self) -> str:
        return self.settings.ollama_model

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.settings.ollama_base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout, connect=5),
            transport=self.transport, trust_env=False,
        )

    async def is_available(self) -> tuple[bool, str]:
        try:
            async with self._client(5) as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
                models = response.json()["models"]
                names = {item["name"] for item in models}
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return False, "Não foi possível consultar o Ollama local. Abra o aplicativo Ollama."
        configured = self.model if ":" in self.model else self.model + ":latest"
        if configured not in names:
            return False, f"Modelo ausente. Execute: ollama pull {self.model}"
        return True, f"Ollama disponível com {self.model}."

    async def chat(self, messages: Sequence[LLMMessage]) -> str:
        payload = {
            "model": self.model, "stream": False, "format": "json",
            "keep_alive": self.settings.ollama_keep_alive,
            "options": {
                "temperature": self.settings.ollama_temperature,
                "num_ctx": self.settings.ollama_num_ctx,
                "num_predict": self.settings.ollama_num_predict,
            },
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        try:
            async with self._client(self.settings.ollama_timeout_seconds) as client:
                response = await client.post("/api/chat", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as error:
            raise LLMTimeoutError(
                "O modelo demorou além do limite. Tente novamente com menos contexto "
                "ou aumente VRE_OLLAMA_TIMEOUT_SECONDS."
            ) from error
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise LLMUnavailableError(
                    f"Modelo ausente. Execute: ollama pull {self.model}"
                ) from error
            raise LLMUnavailableError("O Ollama recusou a geração. Consulte seu log local.") from error
        except httpx.HTTPError as error:
            raise LLMUnavailableError("Ollama inacessível. Abra o aplicativo Ollama.") from error

        try:
            data = response.json()
            if data.get("done_reason") == "length" or data.get("done") is False:
                raise LLMResponseError(
                    "Resposta truncada. Aumente VRE_OLLAMA_NUM_PREDICT para 450 e tente novamente."
                )
            content = data["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Resposta vazia")
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise LLMResponseError("Ollama retornou uma resposta inválida ou vazia.") from error
        return content
