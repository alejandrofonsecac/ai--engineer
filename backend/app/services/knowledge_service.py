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

        return {
            "track_characteristics": self._tracks.get(track, {}),
            "car_characteristics": self._cars.get(car, {}),
            "relevant_setup_knowledge": relevant_parameters,
        }

    @staticmethod
    def _load_json(relative_path: str) -> dict[str, Any]:
        path = KNOWLEDGE_ROOT / relative_path
        with path.open(encoding="utf-8") as file:
            return json.load(file)

