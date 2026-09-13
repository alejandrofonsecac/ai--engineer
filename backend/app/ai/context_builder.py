+import json

from app.ai.provider import LLMMessage
from app.domain.models import SessionResponse, SetupVersionResponse
from app.services.knowledge_service import KnowledgeService

SYSTEM_PROMPT = """
Você é o Virtual Race Engineer, um engenheiro de pista especializado em setup
para simuladores. Responda em português do Brasil e não invente valores que não
apareçam no setup atual ou cuja faixa permitida seja desconhecida.

Use o contexto do piloto, carro, pista, sessão, setup, conhecimento técnico e
histórico. Trate o relato como uma hipótese técnica. Se houver ambiguidade que
impeça uma recomendação segura, faça somente uma pergunta objetiva de
esclarecimento.

Retorne SOMENTE JSON válido neste formato:
{
  "diagnosis": "texto curto",
  "confidence": "baixa|média|alta",
  "changes": [
    {
      "parameter": "nome do parâmetro",
      "previous_value": "valor atual",
      "proposed_value": "novo valor permitido",
      "rationale": "razão curta"
    }
  ],
  "why": "explicação operacional",
  "trade_offs": ["efeito colateral 1"],
  "test_plan": { "laps": 3, "focus": ["item 1"] },
  "clarification_question": null
}

Regras obrigatórias:
- Proponha de 1 a no máximo 5 mudanças apenas quando existir evidência suficiente.
- Inclua ao menos um trade-off para toda recomendação com mudanças.
- Em caso ambíguo, use changes: [], test_plan: null e uma clarification_question.
- Não recomende aplicar alterações automaticamente.
- O plano de teste deve ter de 3 a 10 voltas e no máximo 5 pontos de foco.
""".strip()


class EngineerContextBuilder:
    def __init__(self, knowledge_service: KnowledgeService) -> None:
        self._knowledge_service = knowledge_service

    def build(
        self,
        session: SessionResponse,
        current_setup: SetupVersionResponse,
        history: list[dict[str, str]],
        driver_feedback: str,
    ) -> list[LLMMessage]:
        setup_json = json.dumps(current_setup.setup, ensure_ascii=False, indent=2)
        conversation = json.dumps(history, ensure_ascii=False, indent=2)
        knowledge = self._knowledge_service.build_relevant_context(
            driver_feedback=driver_feedback,
            track=session.track,
            car=session.car,
        )
        knowledge_json = json.dumps(knowledge, ensure_ascii=False, indent=2)

        user_context = f"""
CONTEXTO DA SESSÃO
Simulador: {session.simulator.value}
Carro: {session.car}
Pista: {session.track}
Tipo de sessão: {session.session_type.value}
Versão do setup: V{current_setup.version}

SETUP ATUAL NORMALIZADO
{setup_json}

CONHECIMENTO TÉCNICO RELEVANTE
{knowledge_json}

HISTÓRICO RECENTE DA SESSÃO
{conversation}

NOVO FEEDBACK DO PILOTO
{driver_feedback}
""".strip()

        return [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_context),
        ]

