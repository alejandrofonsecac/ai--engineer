from functools import lru_cache

from app.ai.context_builder import EngineerContextBuilder
from app.ai.ollama_provider import OllamaProvider
from app.repositories.session_repository import SessionRepository
from app.services.engineer_service import EngineerService
from app.services.knowledge_service import KnowledgeService
from app.services.session_service import SessionService


@lru_cache
def get_session_repository() -> SessionRepository:
    return SessionRepository()


def get_session_service() -> SessionService:
    return SessionService(get_session_repository())


def get_ollama_provider() -> OllamaProvider:
    return OllamaProvider()


@lru_cache
def get_engineer_service() -> EngineerService:
    repository = get_session_repository()
    return EngineerService(
        repository=repository,
        session_service=SessionService(repository),
        context_builder=EngineerContextBuilder(KnowledgeService()),
        provider=get_ollama_provider(),
    )
