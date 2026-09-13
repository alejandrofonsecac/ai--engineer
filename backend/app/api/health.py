from fastapi import APIRouter, Depends

from app.ai.ollama_provider import OllamaProvider
from app.api.dependencies import get_ollama_provider
from app.domain.models import LLMHealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/llm", response_model=LLMHealthResponse)
async def llm_health(
    provider: OllamaProvider = Depends(get_ollama_provider),
) -> LLMHealthResponse:
    available, detail = await provider.is_available()
    return LLMHealthResponse(
        available=available,
        model=provider.model,
        detail=detail,
    )

