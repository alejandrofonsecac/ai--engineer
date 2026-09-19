import json
from app.ai.provider import LLMMessage
from app.ai.prompts.engineer_system_prompt import SYSTEM_PROMPT
from app.domain.models import SessionResponse, SetupVersionResponse
from app.services.knowledge_service import KnowledgeService
from app.services.recommendation_guard import setup_candidates, _traction_loss
from app.services.setup_limits import SetupLimits
from app.config import get_settings


class EngineerContextBuilder:
    def __init__(self, knowledge_service: KnowledgeService) -> None:
        self._knowledge_service = knowledge_service

    def build(self, session: SessionResponse, current_setup: SetupVersionResponse,
              history: list[dict[str, str]], driver_feedback: str) -> list[LLMMessage]:
        knowledge = self._knowledge_service.build_relevant_context(
            driver_feedback, session.track, session.car,
        )
        candidates = setup_candidates(
            current_setup.setup, SetupLimits(), get_settings().acc_game_version,
        )
        context = {
            "simulator": session.simulator.value, "car": session.car,
            "track": session.track, "session_type": session.session_type.value,
            "setup_version": current_setup.version, "available_adjustments": candidates,
            "car_characteristics": knowledge["car_characteristics"],
            "track_characteristics": knowledge["track_characteristics"],
            "limits_policy": "unknown não é um intervalo. Valores atuais não revelam mínimos/máximos.",
        }
        if _traction_loss(driver_feedback):
            context["diagnostic_priority"] = (
                "O piloto perde a traseira AO ACELERAR. Investigue patinagem/TC. "
                "Considere TC para cima OU barra traseira para baixo, um teste de cada vez. "
                "Mantenha asa nesta primeira etapa. Uma saída ruim pode reduzir a velocidade final."
            )
        messages = [
            LLMMessage("system", SYSTEM_PROMPT),
            LLMMessage("user", "Contexto da sessão (dados): " + json.dumps(
                context, ensure_ascii=False, separators=(",", ":"))),
        ]
        # Janela curta para o modelo 3B: até duas trocas anteriores e 1600 caracteres.
        recent: list[LLMMessage] = []
        budget = 1600
        for item in reversed(history[-4:]):
            content = item["content"][:800]
            if len(content) > budget:
                break
            recent.insert(0, LLMMessage(item["role"], content))
            budget -= len(content)
        messages.extend(recent)
        messages.append(LLMMessage("user", driver_feedback))
        return messages
