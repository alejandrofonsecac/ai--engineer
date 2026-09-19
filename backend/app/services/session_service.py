from uuid import UUID, uuid4

from app.domain.models import CreateSessionRequest, SessionResponse, SetupVersionResponse
from app.repositories.session_repository import SessionRepository
from app.setup_parsers import ACCSetupParser, InvalidSetupError


class SessionNotFoundError(LookupError):
    pass


class SetupImportError(ValueError):
    pass


class SessionService:
    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    def create(self, request: CreateSessionRequest) -> SessionResponse:
        parsed_setup = None
        if request.setup_file is not None:
            if request.simulator.value != "ACC":
                raise SetupImportError("A importação de setup está disponível apenas para ACC nesta etapa.")
            try:
                parsed_setup = ACCSetupParser().parse(request.setup_file.content)
            except InvalidSetupError as error:
                raise SetupImportError(str(error)) from error
        return self._repository.create(uuid4(), request, parsed_setup)

    def get(self, session_id: UUID) -> SessionResponse:
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError("Sessão não encontrada.")
        return session

    def get_setup_history(self, session_id: UUID) -> list[SetupVersionResponse]:
        self.get(session_id)
        return self._repository.get_setup_history(session_id)

    def get_messages(self, session_id: UUID) -> list[dict[str, str]]:
        self.get(session_id)
        return self._repository.get_messages(session_id, limit=100)
