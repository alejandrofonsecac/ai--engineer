import json
from uuid import UUID

from pydantic import ValidationError

from app.ai.context_builder import EngineerContextBuilder
from app.ai.ollama_provider import OllamaProvider, OllamaUnavailableError
from app.domain.models import (
    ChatMessageResponse,
    EngineerRecommendation,
)
from app.repositories.session_repository import SessionRepository
from app.services.session_service import SessionService


class EngineerService:
    def __init__(
        self,
        repository: SessionRepository,
        session_service: SessionService,
        context_builder: EngineerContextBuilder,
        provider: OllamaProvider,
    ) -> None:
        self._repository = repository
        self._session_service = session_service
        self._context_builder = context_builder
        self._provider = provider

    async def answer(self, session_id: UUID, driver_feedback: str) -> ChatMessageResponse:
        session = self._session_service.get(session_id)
        current_setup = self._repository.get_current_setup(session_id)
        history = self._repository.get_messages(session_id)
        messages = self._context_builder.build(
            session=session,
            current_setup=current_setup,
            history=history,
            driver_feedback=driver_feedback,
        )

        self._repository.add_message(session_id, "user", driver_feedback)
        raw_response = await self._provider.chat(messages)
        recommendation = self._parse_recommendation(raw_response)
        engineer_message = self._to_engineer_message(recommendation)
        self._repository.add_message(session_id, "assistant", engineer_message)

        return ChatMessageResponse(
            session_id=session_id,
            driver_message=driver_feedback,
            engineer_message=engineer_message,
            recommendation=recommendation,
        )

    @staticmethod
    def _parse_recommendation(raw_response: str) -> EngineerRecommendation:
        try:
            parsed = EngineerRecommendation.model_validate(json.loads(raw_response))
        except (json.JSONDecodeError, ValidationError) as error:
            raise OllamaUnavailableError(
                "O modelo retornou uma recomendação em formato inválido. Tente novamente."
            ) from error

        if len(parsed.changes) > 5:
            raise OllamaUnavailableError("O modelo excedeu o limite de cinco alterações.")
        if parsed.changes and parsed.test_plan is None:
            raise OllamaUnavailableError(
                "O modelo recomendou alterações sem um plano de teste."
            )
        if not parsed.changes and not parsed.clarification_question:
            raise OllamaUnavailableError(
                "O modelo não retornou mudanças nem pergunta de esclarecimento."
            )
        return parsed

    @staticmethod
    def _to_engineer_message(recommendation: EngineerRecommendation) -> str:
        if recommendation.clarification_question and not recommendation.changes:
            return recommendation.clarification_question

        changes = "; ".join(
            f"{change.parameter}: {change.previous_value} → {change.proposed_value}"
            for change in recommendation.changes
        )
        trade_offs = " ".join(recommendation.trade_offs)
        return (
            f"{recommendation.diagnosis}\n\n"
            f"Alterações propostas: {changes}.\n\n"
            f"{recommendation.why}\n\n"
            f"Trade-offs: {trade_offs}"
        )

