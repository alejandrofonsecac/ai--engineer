import json
from app.ai.provider import LLMMessage
from app.ai.prompts.engineer_system_prompt import SYSTEM_PROMPT
from app.domain.models import SessionResponse, SetupVersionResponse
from app.services.knowledge_service import KnowledgeService


class EngineerContextBuilder:
    def __init__(self, knowledge_service: KnowledgeService) -> None:
        self._knowledge_service = knowledge_service

    def build(self, session: SessionResponse, current_setup: SetupVersionResponse,
              history: list[dict[str, str]], driver_feedback: str) -> list[LLMMessage]:
        knowledge = self._knowledge_service.build_relevant_context(
            driver_feedback, session.track, session.car,
        )
        setup = json.dumps(current_setup.setup, ensure_ascii=False, separators=(",", ":"))
        # Não truncar JSON de setup: omitir explicitamente se ele exceder o orçamento.
        setup_context = current_setup.setup if len(setup) <= 1600 else {
            "status": "Setup omitido por tamanho; solicitar apenas os parâmetros relevantes."
        }
        context = {
            "simulator": session.simulator.value, "car": session.car,
            "track": session.track, "session_type": session.session_type.value,
            "setup_version": current_setup.version, "current_setup": setup_context,
            "knowledge": knowledge,
        }
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
