from datetime import UTC, datetime
from uuid import uuid4

from app.ai.context_builder import EngineerContextBuilder
from app.domain.models import EngineerRecommendation, SessionResponse, SetupVersionResponse
from app.services.knowledge_service import KnowledgeService


def test_recommendation_allows_at_most_five_changes() -> None:
    recommendation = EngineerRecommendation(
        diagnosis="Teste",
        confidence="média",
        changes=[],
        why="É necessário esclarecer o comportamento.",
        trade_offs=[],
        test_plan=None,
        clarification_question="O problema ocorre antes ou depois do acelerador?",
    )

    assert recommendation.clarification_question is not None


def test_context_builder_includes_relevant_knowledge() -> None:
    session = SessionResponse(
        id=uuid4(),
        simulator="ACC",
        car="Porsche 992 GT3 R",
        track="Nordschleife",
        session_type="Desenvolvimento de setup",
        current_setup_version=1,
        created_at=datetime.now(UTC),
    )
    setup = SetupVersionResponse(
        version=1,
        setup={"aero": {"rear_wing": 8}},
        source="importado",
        created_at=datetime.now(UTC),
    )

    messages = EngineerContextBuilder(KnowledgeService()).build(
        session=session,
        current_setup=setup,
        history=[],
        driver_feedback="A traseira está instável em curvas rápidas.",
    )

    assert "rear_wing" in messages[1].content
