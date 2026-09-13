from uuid import UUID, uuid4

from app.domain.models import CreateSessionRequest, SessionResponse, SetupVersionResponse
from app.repositories.session_repository import SessionRepository


class SessionNotFoundError(LookupError):
    pass


class SessionService:
    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    def create(self, request: CreateSessionRequest) -> SessionResponse:
        return self._repository.create(uuid4(), request)

    def get(self, session_id: UUID) -> SessionResponse:
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError("Sessão não encontrada.")
        return session

    def get_setup_history(self, session_id: UUID) -> list[SetupVersionResponse]:
        self.get(session_id)
        return self._repository.get_setup_history(session_id)

