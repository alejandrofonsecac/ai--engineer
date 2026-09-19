import re
import unicodedata
from typing import Any

from app.config import get_settings
from app.domain.models import (
    AdjustmentChoice, EngineerRecommendation, RecommendationDraft, SetupChange, SetupVersionResponse, TestPlan,
)
from app.services.setup_limits import SetupLimits


PARAMETERS = {
    "traction_control": {
        "label": "Controle de tração (TC1)", "menu": "Electronics → TC1",
        "path": ("electronics", "tC1"),
        "increase": ("ajudar a conter a patinagem ao acelerar", "mais corte de potência pode deixar a saída mais lenta"),
        "decrease": ("diminuir a intervenção do controle de tração", "as rodas podem patinar mais e a traseira escapar"),
    },
    "rear_anti_roll_bar": {
        "label": "Barra estabilizadora traseira", "menu": "Mechanical Grip → ARB Rear",
        "path": ("mechanical_grip", "aRBRear"),
        "increase": ("facilitar a rotação do carro na curva", "a traseira pode perder aderência com mais facilidade"),
        "decrease": ("favorecer a aderência traseira na saída", "o carro pode virar menos e escapar de frente"),
    },
    "rear_wing": {
        "label": "Asa traseira", "menu": "Aero → Rear Wing",
        "path": ("aero", "rearWing"),
        "increase": ("dar mais apoio à traseira em alta velocidade", "mais arrasto pode reduzir a velocidade na reta"),
        "decrease": ("reduzir o arrasto na reta", "menos apoio pode deixar a traseira instável nas curvas rápidas"),
    },
    "front_fast_bump": {
        "label": "Compressão rápida dianteira", "menu": "Dampers → Bump Fast (FL e FR)",
        "path": ("dampers", "bumpFast"), "corners": (0, 1),
        "increase": ("dar mais suporte à dianteira em impactos", "a dianteira pode ficar mais seca e pular sobre zebras"),
        "decrease": ("deixar a dianteira absorver melhor zebras", "pode aumentar mergulho e perder precisão em mudanças de direção"),
    },
    "rear_fast_bump": {
        "label": "Compressão rápida traseira", "menu": "Dampers → Bump Fast (RL e RR)",
        "path": ("dampers", "bumpFast"), "corners": (2, 3),
        "increase": ("dar mais suporte à traseira em impactos", "a traseira pode pular e perder aderência sobre zebras"),
        "decrease": ("deixar a traseira absorver melhor zebras", "pode aumentar o movimento da traseira em transições rápidas"),
    },
    "front_fast_rebound": {
        "label": "Retorno rápido dianteiro", "menu": "Dampers → Rebound Fast (FL e FR)",
        "path": ("dampers", "reboundFast"), "corners": (0, 1),
        "increase": ("controlar a extensão dianteira após um impacto", "a roda pode demorar a reassentar e perder contato"),
        "decrease": ("permitir que a roda dianteira reassente mais rápido", "pode deixar a dianteira mais solta depois da zebra"),
    },
    "rear_fast_rebound": {
        "label": "Retorno rápido traseiro", "menu": "Dampers → Rebound Fast (RL e RR)",
        "path": ("dampers", "reboundFast"), "corners": (2, 3),
        "increase": ("controlar a extensão traseira após um impacto", "a roda traseira pode demorar a reassentar e perder tração"),
        "decrease": ("permitir que a roda traseira reassente mais rápido", "pode deixar a traseira mais solta após a zebra"),
    },
}


def _value(setup: dict, path: tuple[str, ...]) -> int | None:
    value: Any = setup
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value if type(value) is int and value >= 0 else None


def _corner_values(setup: dict, path: tuple[str, ...], corners: tuple[int, int]) -> tuple[int, int] | None:
    value: Any = setup
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    if not isinstance(value, list) or len(value) != 4:
        return None
    selected = tuple(value[index] for index in corners)
    return selected if all(type(item) is int and item >= 0 for item in selected) else None


def setup_candidates(setup: dict, limits: SetupLimits, version: str | None) -> dict:
    metadata = setup.get("metadata", {})
    if not isinstance(metadata, dict) or metadata.get("source_format") != "ACC":
        return {}
    candidates = {}
    for key, spec in PARAMETERS.items():
        corners = spec.get("corners")
        current = (_corner_values(setup, spec["path"], corners) if corners
                   else _value(setup, spec["path"]))
        if current is None:
            continue
        profile = limits.find(setup, key, version)
        candidates[key] = {
            "label": spec["label"], "value_in_file": current,
            "limits": ({"min": profile.raw_min, "max": profile.raw_max,
                        "step": profile.raw_step} if profile else "unknown"),
            "increase": {"benefit": spec["increase"][0], "risk": spec["increase"][1]},
            "decrease": {"benefit": spec["decrease"][0], "risk": spec["decrease"][1]},
        }
    return candidates


def _traction_loss(feedback: str) -> bool:
    text = "".join(char for char in unicodedata.normalize("NFD", feedback.lower())
                   if not unicodedata.combining(char))
    for clause in re.split(r"[.!?;]|\bmas\b|\bporem\b", text):
        if re.search(r"\bnao\b", clause):
            continue
        loss = any(term in clause for term in ("escap", "solta", "sobrester", "perde o equilibrio", "saindo", "patin"))
        if loss and any(term in clause for term in ("traseira", "equilibrio", "patin")) and "aceler" in clause:
            return True
    return False


def _rear_loss_on_curbs(feedback: str) -> bool:
    text = "".join(char for char in unicodedata.normalize("NFD", feedback.lower())
                   if not unicodedata.combining(char))
    return ("zebra" in text and "traseira" in text
            and any(term in text for term in ("escap", "solta", "instavel", "saindo", "perde")))


class RecommendationGuard:
    def __init__(self, limits: SetupLimits | None = None, game_version: str | None = None):
        self.limits = limits or SetupLimits()
        self.game_version = game_version or get_settings().acc_game_version

    def apply(self, draft: RecommendationDraft, current_setup: SetupVersionResponse,
              driver_feedback: str) -> EngineerRecommendation:
        setup = current_setup.setup
        candidates = setup_candidates(setup, self.limits, self.game_version)
        traction_loss = _traction_loss(driver_feedback)
        rear_loss_on_curbs = _rear_loss_on_curbs(driver_feedback)
        changes: list[SetupChange] = []
        notes: list[str] = []
        missing_limits: list[str] = []
        seen: set[str] = set()
        choices = list(draft.choices)
        # Zebra + traseira solta é um pedido explícito sobre amortecedores. Se o
        # modelo local não escolher uma opção apesar de ela estar no setup,
        # ofereça a intervenção mínima e direcional nas duas rodas traseiras.
        if rear_loss_on_curbs and not any(choice.parameter.startswith("rear_fast_") for choice in choices):
            choices.insert(0, AdjustmentChoice(
                parameter="rear_fast_bump", direction="decrease", clicks=1,
            ))
        for choice in choices:
            key, direction, clicks = choice.parameter, choice.direction, choice.clicks
            if key not in candidates or key in seen:
                continue
            seen.add(key)
            if direction not in ("increase", "decrease"):
                notes.append(f"Não foi possível interpretar a direção de ajuste para {key}.")
                continue
            if traction_loss and ((key in ("rear_wing", "traction_control") and direction == "decrease")
                                  or (key == "rear_anti_roll_bar" and direction == "increase")):
                notes.append("Mantenha esse ajuste por enquanto: a direção proposta pode piorar a perda da traseira ao acelerar.")
                continue
            spec = PARAMETERS[key]
            current = candidates[key]["value_in_file"]
            profile = self.limits.find(setup, key, self.game_version)
            verb = "Aumente" if direction == "increase" else "Reduza"
            action_labels = {
                "traction_control": "o TC1", "rear_anti_roll_bar": "a barra estabilizadora traseira",
                "rear_wing": "a asa traseira",
            }
            action = f"{verb} {action_labels.get(key, spec['label'].lower())}"
            if profile:
                target = profile.target(current, direction, clicks)
                if target is None:
                    notes.append(f"Mantenha {spec['label']}: o próximo clique não está dentro do intervalo validado ou o valor importado é incompatível.")
                    continue
                before, after = current + profile.display_offset, target + profile.display_offset
                click_label = "clique" if clicks == 1 else "cliques"
                action += f" em {clicks} {click_label}: {before} → {after}"
                value_label = str(before)
                limits_note = (f"Intervalo de referência: {profile.raw_min + profile.display_offset} a "
                               f"{profile.raw_max + profile.display_offset} (catálogo comunitário).")
            else:
                action += "; confirme o intervalo no jogo antes de escolher quantos cliques"
                if isinstance(current, tuple):
                    labels = ("FL", "FR") if spec["corners"] == (0, 1) else ("RL", "RR")
                    value_label = f"{labels[0]} {current[0]} / {labels[1]} {current[1]} no arquivo"
                else:
                    value_label = f"{current} no arquivo"
                limits_note = "Mínimo, máximo e correspondência com o menu ainda não confirmados."
                missing_limits.append(spec["label"])
            benefit, risk = spec[direction]
            changes.append(SetupChange(
                parameter=spec["label"], current_value=value_label,
                recommended_adjustment=action, rationale=f"Teste essa direção para {benefit}.",
                positive_effects=[benefit], negative_effects=[risk],
                menu=spec["menu"], limits_note=limits_note,
            ))
            if len(changes) == 2:
                break

        if traction_loss and "rear_wing" in candidates and not any(change.parameter == "Asa traseira" for change in changes):
            notes.append(f"Mantenha a asa traseira por enquanto (arquivo: {candidates['rear_wing']['value_in_file']}). Primeiro estabilize a saída; tirar asa pode piorar a traseira nas curvas rápidas.")
        if not candidates:
            question = "Importe o setup JSON do ACC desta sessão para eu conferir os ajustes disponíveis."
        elif missing_limits:
            question = (f"No menu do jogo, qual o valor atual, mínimo e máximo de {missing_limits[0]}? "
                        "Informe também a versão do ACC para confirmar os cliques.")
        else:
            question = draft.clarification_question
        if traction_loss and candidates and not missing_limits:
            question = "Ao acelerar, as rodas patinam ou você sente o motor cortar potência?"
        if not changes and not question:
            question = "A traseira escapa ao frear, no meio da curva ou ao acelerar? O TC está cortando potência?"

        # Um teste relatado pode ter mudado o carro fora do aplicativo. Não tratar
        # o JSON antigo como se fosse uma leitura em tempo real do simulador.
        reported_edit = re.search(r"\b(testei|aumentei|reduzi|alterei|mudei|diminu[ií])\b.{0,80}\b(tc\d*|asa|barra|amortec|bump|rebound)\b", driver_feedback.lower())
        if changes and reported_edit:
            changes = []
            question = "Qual é o valor atual no menu depois do seu teste? Importe o setup atualizado para eu recalcular os cliques."
            notes.append("O arquivo importado pode ser anterior ao ajuste que você testou; confirme a configuração atual antes de outra mudança.")
        elif changes and not missing_limits:
            # A instrução acionável já contém o próximo teste. Perguntas do LLM
            # neste ponto frequentemente repetem ou contradizem o ajuste calculado.
            question = None

        why = "Teste uma alteração de cada vez. Se piorar, volte ao ajuste anterior antes de experimentar a próxima."
        if any(term in driver_feedback.lower() for term in ("velocidade final", "final de reta", "km/h")):
            why += " Compare a velocidade no início e no fim da reta, com o mesmo combustível e condições; a perda pode começar na saída da curva."
        focus = ["Compare as correções de volante e a patinagem na saída",
                 "Observe se o TC corta potência e se a aceleração piora",
                 "Compare a velocidade no início e no fim da mesma reta"]
        if not traction_loss:
            focus = ["Compare o comportamento na mesma curva e nas mesmas condições",
                     "Observe o benefício e o efeito negativo do ajuste testado"]
        diagnosis = draft.diagnosis
        if traction_loss:
            diagnosis = "A traseira pode estar perdendo aderência quando você acelera. Vamos investigar a patinagem e a atuação do controle de tração antes de mexer na asa."
        elif "tc" in driver_feedback.lower() and any(term in driver_feedback.lower() for term in ("cort", "interven")):
            diagnosis = "O controle de tração pode estar cortando mais potência do que o necessário. É preciso comparar a aceleração sem provocar patinagem."
            if candidates and not reported_edit and not missing_limits:
                question = "Depois do teste, a aceleração melhorou sem as rodas patinarem?"
        return EngineerRecommendation(
            diagnosis=diagnosis,
            confidence=("média" if draft.confidence.lower() in ("média", "media") else "baixa") if changes and not traction_loss else "baixa",
            changes=changes, why=why,
            trade_offs=list(dict.fromkeys(notes))[:5] or ["Interrompa o teste e reverta o ajuste se o carro ficar mais difícil de controlar."],
            test_plan=TestPlan(laps=3, focus=focus), clarification_question=question,
        )
