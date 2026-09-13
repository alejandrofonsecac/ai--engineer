from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


class LLMProvider(Protocol):
    @property
    def model(self) -> str: ...

    async def is_available(self) -> tuple[bool, str]: ...

    async def chat(self, messages: Sequence[LLMMessage]) -> str: ...

