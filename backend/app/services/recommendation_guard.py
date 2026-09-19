from typing import Any

from app.domain.models import EngineerRecommendation, SetupChange, SetupVersionResponse, TestPlan


class RecommendationGuard:
    """Vincula sugestões do LLM ao setup e aplica regras técnicas conservadoras."""

    def apply(
        self,
        recommendation: EngineerRecommendation,
        current_setup: SetupVersionResponse,
        driver_feedback: str,
    ) -> EngineerRecommendation:
        setup = current_setup.setup
        feedback = driver_feedback.lower()
        on_throttle_instability = (
            any(word in feedback for word in ("traseira", "sobrester", "perde o equilíbrio"))
            and any(word in feedback for word in ("aceler", "tração", "saída"))
        )
        top_speed_concern = any(
            phrase in feedback
            for phrase in ("velocidade final", "final de reta", "reta abaixo", "km/h")
        )

        if on_throttle_instability:
            changes = self._traction_changes(setup)
            trade_offs = [
                "Mais controle de tração pode cortar potência e reduzir a aceleração na saída.",
                "Uma traseira mecanicamente mais aderente pode diminuir a rotação e aumentar o subesterço.",
            ]
            why = (
                "Primeiro estabilize a entrega de potência e a aderência mecânica traseira. "
                "A diferença de velocidade final também pode começar numa saída de curva ruim, "
                "por isso compare a velocidade de entrada na reta antes de retirar apoio aerodinâmico."
            )
            if top_speed_concern:
                trade_offs.append(
                    "Reduzir asa traseira ou convergência traseira pode melhorar a velocidade "
                    "final, mas tende a piorar justamente a instabilidade relatada; teste isso "
                    "somente depois de estabilizar a tração."
                )
            return recommendation.model_copy(update={
                "confidence": "média",
                "changes": changes,
                "why": why,
                "trade_offs": trade_offs,
                "test_plan": TestPlan(
                    laps=5,
                    focus=[
                        "patinagem e atuação do TC nas saídas de curva",
                        "correções de volante durante a aceleração",
                        "velocidade na entrada e no fim da reta com uma saída limpa",
                    ],
                ),
                "clarification_question": None,
            })

        return recommendation.model_copy(
            update={"changes": self._bind_known_changes(recommendation.changes, setup)}
        )

    def _traction_changes(self, setup: dict[str, Any]) -> list[SetupChange]:
        changes: list[SetupChange] = []
        tc1 = self._get(setup, "electronics", "tC1")
        if tc1 is not None:
            changes.append(SetupChange(
                parameter="Controle de tração (TC1)",
                current_value=self._display(tc1),
                recommended_adjustment="aumentar gradualmente e testar",
                rationale="Controlar a patinagem quando o torque chega às rodas traseiras.",
                positive_effects=["mais estabilidade e previsibilidade sob aceleração"],
                negative_effects=["mais corte de potência e possível perda de aceleração"],
            ))
        rear_arb = self._get(setup, "mechanical_grip", "aRBRear")
        if rear_arb is not None:
            changes.append(SetupChange(
                parameter="Barra estabilizadora traseira",
                current_value=self._display(rear_arb),
                recommended_adjustment="reduzir gradualmente e testar",
                rationale="Aumentar a aderência mecânica do eixo traseiro durante a saída.",
                positive_effects=["melhor tração e traseira mais progressiva"],
                negative_effects=["menor rotação e possível aumento de subesterço"],
            ))
        return changes

    def _bind_known_changes(
        self, changes: list[SetupChange], setup: dict[str, Any]
    ) -> list[SetupChange]:
        paths = {
            "rear_wing": ("Asa traseira", ("aero", "rearWing")),
            "rear_toe": ("Convergência traseira", ("alignment", "toe")),
            "traction_control": ("Controle de tração (TC1)", ("electronics", "tC1")),
            "rear_anti_roll_bar": (
                "Barra estabilizadora traseira", ("mechanical_grip", "aRBRear"),
            ),
            "differential_preload": (
                "Pré-carga do diferencial", ("mechanical_grip", "drivetrain", "preload"),
            ),
        }
        bound: list[SetupChange] = []
        for change in changes:
            key = change.parameter.strip().lower().replace(" ", "_")
            if key not in paths:
                continue
            label, path = paths[key]
            value = self._get(setup, *path)
            if value is None:
                continue
            if key == "rear_toe" and isinstance(value, list) and len(value) >= 4:
                value = value[2:4]
            bound.append(change.model_copy(update={
                "parameter": label,
                "current_value": self._display(value),
            }))
        return bound

    @staticmethod
    def _get(source: dict[str, Any], *path: str) -> Any:
        value: Any = source
        for key in path:
            if not isinstance(value, dict) or key not in value:
                return None
            value = value[key]
        return value

    @staticmethod
    def _display(value: Any) -> str:
        if isinstance(value, list):
            return " / ".join(str(item) for item in value)
        return str(value)
