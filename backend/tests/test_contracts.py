from datetime import UTC, datetime
from uuid import uuid4
import copy
import pytest
from pydantic import ValidationError

from app.ai.context_builder import EngineerContextBuilder
from app.domain.models import (
    EngineerRecommendation, RecommendationDraft, SessionResponse, SetupVersionResponse,
)
from app.services.knowledge_service import KnowledgeService
from app.services.recommendation_guard import RecommendationGuard
from app.services.setup_limits import ParameterLimits, SetupLimits


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
        setup={"metadata": {"source_format": "ACC"}, "aero": {"rearWing": 8}},
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


def test_low_speed_traction_omits_aero():
    knowledge = KnowledgeService().build_relevant_context(
        "A traseira escapa quando acelero em curvas lentas.",
        "Nürburgring Nordschleife", "Porsche 992 GT3 R",
    )
    ids = {item["id"] for item in knowledge["relevant_setup_knowledge"]}
    assert "rear_wing" not in ids
    assert "differential_preload" in ids
    assert knowledge["track_characteristics"]["surface"] == "irregular"


def imported_setup(**overrides):
    data = {
        "metadata": {"source_format": "ACC", "car_name": "ford_mustang_gt3", "track_bop_type": 35},
        "electronics": {"tC1": 3},
        "mechanical_grip": {"aRBRear": 2},
        "aero": {"rearWing": 6},
        "dampers": {"bumpFast": [6, 6, 6, 6], "reboundFast": [8, 8, 8, 8]},
    }
    data.update(overrides)
    return SetupVersionResponse(
        version=1,
        setup=data,
        source="importado",
        created_at=datetime.now(UTC),
    )


def draft(*choices):
    selected = []
    for choice in choices:
        item = {"parameter": choice[0], "direction": choice[1]}
        if len(choice) == 3:
            item["clicks"] = choice[2]
        selected.append(item)
    return RecommendationDraft(
        diagnosis="Instabilidade sob aceleração.",
        confidence="baixa",
        choices=selected,
        clarification_question=None,
    )


FEEDBACK = "O carro está saindo muito de traseira e quando eu tento acelerar ele perde o equilíbrio. Além que o carro está a 3km/h de velocidade final de reta abaixo do ideal. Quais alterações você recomenda eu tomar?"


def test_real_setup_values_become_bounded_clicks_without_mutating_import():
    setup = imported_setup()
    original = copy.deepcopy(setup)
    guarded = RecommendationGuard(game_version="1.10.3").apply(
        draft(("traction_control", "increase"), ("rear_anti_roll_bar", "decrease")), setup, FEEDBACK,
    )
    assert "3 → 4" in guarded.changes[0].recommended_adjustment
    assert "2 → 1" in guarded.changes[1].recommended_adjustment
    assert "1 clique" in guarded.changes[0].recommended_adjustment
    assert guarded.changes[0].menu == "Electronics → TC1"
    assert "Mantenha a asa" in guarded.trade_offs[0]
    assert "uma alteração de cada vez" in guarded.why
    assert setup == original


def test_rear_wing_can_recommend_two_bounded_clicks_with_clear_tradeoff():
    guarded = RecommendationGuard(game_version="1.10.3").apply(
        draft(("rear_wing", "increase", 2)), imported_setup(),
        "A traseira fica instável somente nas curvas rápidas; a saída está boa.",
    )
    change = guarded.changes[0]
    assert "2 cliques: 6 → 8" in change.recommended_adjustment
    assert "apoio" in change.positive_effects[0]
    assert "velocidade na reta" in change.negative_effects[0]
    assert guarded.clarification_question is None


def test_rear_fast_bump_is_available_as_a_directional_pair_for_curbs():
    guarded = RecommendationGuard(game_version="1.10.3").apply(
        draft(("rear_fast_bump", "decrease")), imported_setup(),
        "A traseira escapa quando passo nas zebras em Spa.",
    )
    change = guarded.changes[0]
    assert change.parameter == "Compressão rápida traseira"
    assert "Reduza compressão rápida traseira" in change.recommended_adjustment
    assert "RL 6 / RR 6" in change.current_value
    assert "absorver melhor zebras" in change.positive_effects[0]
    assert "movimento da traseira" in change.negative_effects[0]


def test_rear_loss_on_curbs_has_a_damper_fallback_when_model_omits_choice():
    guarded = RecommendationGuard(game_version="1.10.3").apply(
        draft(), imported_setup(), "A traseira escapa bastante nas zebras em Spa.",
    )
    assert guarded.changes[0].parameter == "Compressão rápida traseira"


def test_new_parameter_id_does_not_make_the_draft_contract_invalid():
    result = RecommendationDraft.model_validate({
        "diagnosis": "Teste", "confidence": "média",
        "choices": [{"parameter": "rear_fast_bump", "direction": "decrease", "clicks": 1}],
        "clarification_question": None,
    })
    assert result.choices[0].parameter == "rear_fast_bump"


@pytest.mark.parametrize("current,direction", [(0,"decrease"), (11,"increase"), (12,"decrease")])
def test_limits_and_invalid_current_block_clicks(current, direction):
    guarded = RecommendationGuard(game_version="1.10.3").apply(
        draft(("traction_control", direction)), imported_setup(electronics={"tC1": current}),
        "O TC está intervindo demais.",
    )
    assert guarded.changes == []


def test_without_limits_no_numeric_target_is_invented():
    guarded = RecommendationGuard(limits=SetupLimits([])).apply(
        draft(("traction_control", "increase")), imported_setup(), FEEDBACK,
    )
    assert "→" not in guarded.changes[0].recommended_adjustment
    assert "mínimo e máximo" in guarded.clarification_question


@pytest.mark.parametrize("metadata,version", [
    ({"source_format": "ACC", "car_name": "other_car", "track_bop_type": 35}, "1.10.3"),
    ({"source_format": "ACC", "car_name": "ford_mustang_gt3", "track_bop_type": 34}, "1.10.3"),
    ({"source_format": "ACC", "car_name": "ford_mustang_gt3", "track_bop_type": 35}, "1.9"),
])
def test_no_cross_car_bop_or_version_limits(metadata, version):
    guarded = RecommendationGuard(game_version=version).apply(
        draft(("traction_control", "increase")), imported_setup(metadata=metadata), FEEDBACK,
    )
    assert "→" not in guarded.changes[0].recommended_adjustment


def test_conflicts_blocked_without_replacing_model_choice_with_fixed_recipe():
    result = RecommendationGuard().apply(
        draft(("rear_wing", "decrease"), ("traction_control", "decrease")), imported_setup(), FEEDBACK,
    )
    assert result.changes == []
    assert result.clarification_question


def test_negation_does_not_force_traction_recipe():
    result = RecommendationGuard(game_version="1.10.3").apply(
        draft(("traction_control", "decrease")), imported_setup(),
        "A traseira não escapa ao acelerar. O TC corta demais e perdi velocidade.",
    )
    assert len(result.changes) == 1
    assert "3 → 2" in result.changes[0].recommended_adjustment


@pytest.mark.parametrize("value", [True, "3", -1, {}, [3], 3.5])
def test_malformed_parameter_never_becomes_a_click(value):
    result = RecommendationGuard().apply(
        draft(("traction_control", "increase")), imported_setup(electronics={"tC1": value}), FEEDBACK,
    )
    assert result.changes == []


def test_missing_setup_never_produces_changes():
    result = RecommendationGuard().apply(
        draft(("traction_control", "increase")), imported_setup(metadata={}), FEEDBACK,
    )
    assert result.changes == []
    assert "Importe" in result.clarification_question


def test_non_unit_step_and_display_offset():
    profile = ParameterLimits(car="fixture", game_version="test", track_bop_type=0,
        parameter="traction_control", raw_min=0, raw_max=10, raw_step=2,
        display_offset=1, source="synthetic test only")
    assert profile.target(4, "increase") == 6
    assert profile.target(3, "increase") is None


def test_reported_external_change_requires_current_setup_before_new_target():
    result = RecommendationGuard(game_version="1.10.3").apply(
        draft(("traction_control", "decrease")), imported_setup(),
        "Testei aumentar TC1 e o motor corta demais. A traseira não escapa ao acelerar.",
    )
    assert result.changes == []
    assert "setup atualizado" in result.clarification_question


def test_braking_report_does_not_force_tc_changes():
    result = RecommendationGuard().apply(draft(), imported_setup(),
        "A traseira escapa só quando freio. Ao acelerar está estável.")
    assert result.changes == []
    assert "perdendo aderência quando você acelera" not in result.diagnosis


def test_duplicate_choices_are_deduplicated():
    result = RecommendationGuard(game_version="1.10.3").apply(
        draft(("traction_control", "increase"), ("traction_control", "decrease")),
        imported_setup(), "O TC precisa de ajuste.",
    )
    assert len(result.changes) == 1


def test_model_cannot_supply_target_values():
    with pytest.raises(ValidationError):
        RecommendationDraft.model_validate({
            "diagnosis": "Teste", "confidence": "baixa", "clarification_question": None,
            "choices": [{"parameter": "traction_control", "direction": "increase", "target": 99}],
        })
