import json
from pathlib import Path
from typing import Any

KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "knowledge"


class KnowledgeService:
    def __init__(self) -> None:
        self._effects = self._load_json("setup/effects.json")
        self._tracks = self._load_json("tracks/profiles.json")
        self._cars = self._load_json("cars/profiles.json")

    def build_relevant_context(
        self, driver_feedback: str, track: str, car: str
    ) -> dict[str, Any]:
        feedback = driver_feedback.lower()
        relevant_parameters = [
            item
            for item in self._effects.get("parameters", [])
            if any(keyword in feedback for keyword in item.get("keywords", []))
        ]
        low_speed = any(word in feedback for word in ("lenta", "lento", "baixa"))
        on_throttle = any(word in feedback for word in ("aceler", "tração", "saída"))
        if low_speed and on_throttle:
            relevant_parameters = [
                item for item in self._effects.get("parameters", [])
                if item["id"] in (
                    "differential_preload", "rear_toe", "traction_control",
                    "rear_anti_roll_bar",
                )
            ]

        rear_instability = any(word in feedback for word in ("traseira", "sobrester", "equilíbrio"))
        top_speed = any(word in feedback for word in ("velocidade final", "final de reta", "km/h"))
        decision_guidance = {}
        if rear_instability and on_throttle:
            decision_guidance = {
                "prioritize": ["increase traction_control", "decrease rear_anti_roll_bar"],
                "avoid_in_same_cycle": ["decrease rear_wing", "decrease rear_toe"],
                "reason": (
                    "Reducing rear wing or rear toe may help top speed but can worsen "
                    "the reported on-throttle rear instability."
                ) if top_speed else "Prioritize rear traction before aerodynamic changes.",
            }

        track_key = "Nordschleife" if track in ("Nordschleife", "Nürburgring Nordschleife") else track
        return {
            "status": "Base inicial ilustrativa; não contém limites validados por simulador.",
            "track_characteristics": self._tracks.get(track_key, {}),
            "car_characteristics": self._cars.get(car, {}),
            "relevant_setup_knowledge": relevant_parameters[:4],
            "decision_guidance": decision_guidance,
        }

    @staticmethod
    def _load_json(relative_path: str) -> dict[str, Any]:
        path = KNOWLEDGE_ROOT / relative_path
        with path.open(encoding="utf-8") as file:
            return json.load(file)
