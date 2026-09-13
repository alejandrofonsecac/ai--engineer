from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_engineer_service, get_session_service
from app.ai.ollama_provider import OllamaUnavailableError
from app.domain.models import (
    ChatMessageRequest,
    ChatMessageResponse,
    CreateSessionRequest,
    SessionResponse,
    SetupVersionResponse,
)
from app.services.engineer_service import EngineerService
from app.services.session_service import SessionNotFoundError, SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: CreateSessionRequest,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    return service.create(request)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: UUID,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        return service.get(session_id)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{session_id}/setup/history", response_model=list[SetupVersionResponse])
def get_setup_history(
    session_id: UUID,
    service: SessionService = Depends(get_session_service),
) -> list[SetupVersionResponse]:
    try:
        return service.get_setup_history(session_id)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: UUID,
    request: ChatMessageRequest,
    service: EngineerService = Depends(get_engineer_service),
) -> ChatMessageResponse:
    try:
        return await service.answer(session_id, request.content)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except OllamaUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

