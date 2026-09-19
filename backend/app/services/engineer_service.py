import asyncio
import logging
from uuid import UUID
from pydantic import ValidationError
from app.ai.context_builder import EngineerContextBuilder
from app.ai.provider import LLMProvider, LLMResponseError
from app.domain.models import ChatMessageResponse, EngineerRecommendation
from app.repositories.session_repository import SessionRepository
from app.services.session_service import SessionService
from app.services.recommendation_guard import RecommendationGuard

logger = logging.getLogger(__name__)


class EngineerBusyError(RuntimeError):
    pass


class EngineerService:
    def __init__(self, repository: SessionRepository, session_service: SessionService,
                 context_builder: EngineerContextBuilder, provider: LLMProvider) -> None:
        self._repository = repository
        self._session_service = session_service
        self._context_builder = context_builder
        self._provider = provider
        self._generation_lock = asyncio.Lock()

    async def answer(self, session_id: UUID, driver_feedback: str) -> ChatMessageResponse:
        if self._generation_lock.locked():
            raise EngineerBusyError("O engenheiro está respondendo outra mensagem. Aguarde.")
        async with self._generation_lock:
            session = self._session_service.get(session_id)
            current_setup = self._repository.get_current_setup(session_id)
            history = self._repository.get_messages(session_id)
            messages = self._context_builder.build(
                session, current_setup, history, driver_feedback,
            )
            raw_response = await self._provider.chat(
                messages,
                response_schema=EngineerRecommendation.model_json_schema(),
            )
            recommendation = self._parse_recommendation(raw_response)
            recommendation = RecommendationGuard().apply(
                recommendation, current_setup, driver_feedback,
            )
            engineer_message = self._to_engineer_message(recommendation)
            # Uma troca completa é atômica. Falhas não deixam mensagens órfãs.
            self._repository.add_exchange(session_id, driver_feedback, engineer_message)
            return ChatMessageResponse(
                session_id=session_id, driver_message=driver_feedback,
                engineer_message=engineer_message, recommendation=recommendation,
            )

    @staticmethod
    def _parse_recommendation(raw_response: str) -> EngineerRecommendation:
        try:
            return EngineerRecommendation.model_validate_json(raw_response)
        except (ValueError, ValidationError) as error:
            logger.warning(
                "Resposta estruturada inválida do LLM: %s; conteúdo=%r",
                error,
                raw_response[:4000],
            )
            raise LLMResponseError(
                "O modelo não conseguiu montar uma recomendação válida. Tente novamente."
            ) from error

    @staticmethod
    def _to_engineer_message(recommendation: EngineerRecommendation) -> str:
        parts = [
            f"Diagnóstico ({recommendation.confidence} confiança): "
            + recommendation.diagnosis
        ]
        if recommendation.changes:
            changes = ["Alterações recomendadas:"]
            for change in recommendation.changes:
                changes.append(
                    f"• {change.parameter} (atual: {change.current_value}): "
                    f"{change.recommended_adjustment}. {change.rationale}\n"
                    f"  Benefício: {'; '.join(change.positive_effects)}. "
                    f"Possível efeito negativo: {'; '.join(change.negative_effects)}."
                )
            parts.append("\n".join(changes))
        parts.append("Por quê: " + recommendation.why)
        if recommendation.trade_offs:
            parts.append("Trade-offs: " + "; ".join(recommendation.trade_offs))
        if recommendation.test_plan:
            parts.append(
                f"Teste: {recommendation.test_plan.laps} voltas. "
                + "; ".join(recommendation.test_plan.focus)
            )
        if recommendation.clarification_question:
            parts.append(recommendation.clarification_question)
        return "\n\n".join(parts)
