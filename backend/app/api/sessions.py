from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_engineer_service, get_session_service
from app.ai.provider import LLMUnavailableError, LLMResponseError, LLMTimeoutError
from app.domain.models import (
    ChatMessageRequest,
    ChatMessageResponse,
    CreateSessionRequest,
    SessionResponse,
    SetupVersionResponse,
    StoredMessageResponse,
)
from app.services.engineer_service import EngineerService, EngineerBusyError
from app.services.session_service import SessionNotFoundError, SessionService, SetupImportError

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: CreateSessionRequest,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        return service.create(request)
    except SetupImportError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


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


@router.get("/{session_id}/messages", response_model=list[StoredMessageResponse])
def get_messages(
    session_id: UUID,
    service: SessionService = Depends(get_session_service),
) -> list[dict[str, str]]:
    try:
        return service.get_messages(session_id)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


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
    except EngineerBusyError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except LLMTimeoutError as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except LLMResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except LLMUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
