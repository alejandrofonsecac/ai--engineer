from copy import deepcopy
from dataclasses import dataclass
from typing import Any


class InvalidSetupError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedSetup:
    normalized: dict[str, Any]
    original: dict[str, Any]
    source_car_name: str


class ACCSetupParser:
    """Valida a estrutura do arquivo do ACC e a converte para categorias internas."""

    _basic_sections = ("tyres", "alignment", "electronics", "strategy")
    _advanced_sections = ("mechanicalBalance", "dampers", "aeroBalance", "drivetrain")

    def parse(self, content: dict[str, Any]) -> ParsedSetup:
        car_name = content.get("carName")
        if not isinstance(car_name, str) or not car_name.strip():
            raise InvalidSetupError("O setup do ACC não possui um carName válido.")

        basic = self._object(content, "basicSetup")
        advanced = self._object(content, "advancedSetup")
        for section in self._basic_sections:
            self._object(basic, section)
        for section in self._advanced_sections:
            self._object(advanced, section)

        normalized = {
            "metadata": {
                "source_format": "ACC",
                "car_name": car_name,
                "track_bop_type": content.get("trackBopType"),
            },
            "tyres": deepcopy(basic["tyres"]),
            "electronics": deepcopy(basic["electronics"]),
            "mechanical_grip": {
                **deepcopy(advanced["mechanicalBalance"]),
                "drivetrain": deepcopy(advanced["drivetrain"]),
            },
            "dampers": deepcopy(advanced["dampers"]),
            "aero": deepcopy(advanced["aeroBalance"]),
            "alignment": deepcopy(basic["alignment"]),
            "strategy": deepcopy(basic["strategy"]),
        }
        return ParsedSetup(
            normalized=normalized,
            original=deepcopy(content),
            source_car_name=car_name,
        )

    @staticmethod
    def _object(parent: dict[str, Any], key: str) -> dict[str, Any]:
        value = parent.get(key)
        if not isinstance(value, dict):
            raise InvalidSetupError(f'O setup do ACC não possui a seção obrigatória "{key}".')
        return value
