from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class LLMUnavailableError(RuntimeError):
    """Serviço local indisponível ou modelo ausente."""


class LLMTimeoutError(LLMUnavailableError):
    """Tempo de geração excedido."""


class LLMResponseError(RuntimeError):
    """Resposta do modelo incompleta ou incompatível com o contrato."""


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


class LLMProvider(Protocol):
    @property
    def model(self) -> str: ...
    async def is_available(self) -> tuple[bool, str]: ...
    async def chat(self, messages: Sequence[LLMMessage]) -> str: ...
