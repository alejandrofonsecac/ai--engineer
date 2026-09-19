"""Limites revisados fora do LLM: nunca inferidos de um único setup."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ParameterLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    car: str = Field(min_length=1)
    game_version: str = Field(min_length=1)
    track_bop_type: int
    parameter: str = Field(min_length=1)
    raw_min: int
    raw_max: int
    raw_step: int = Field(gt=0)
    # Mapeamento verificado para o número exibido na interface do jogo.
    display_offset: int
    source: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_range(self) -> "ParameterLimits":
        if self.raw_max <= self.raw_min or (self.raw_max - self.raw_min) % self.raw_step:
            raise ValueError("Intervalo de cliques inválido.")
        return self

    def target(self, current: int, direction: str, clicks: int = 1) -> int | None:
        if not self.raw_min <= current <= self.raw_max:
            return None
        if (current - self.raw_min) % self.raw_step:
            return None
        if clicks not in (1, 2):
            return None
        change = self.raw_step * clicks
        target = current + (change if direction == "increase" else -change)
        return target if self.raw_min <= target <= self.raw_max else None


class SetupLimits:
    def __init__(self, profiles: list[ParameterLimits] | None = None) -> None:
        if profiles is None:
            path = Path(__file__).resolve().parents[1] / "knowledge/setup/limits.json"
            profiles = [ParameterLimits.model_validate(item) for item in
                        json.loads(path.read_text(encoding="utf-8"))["profiles"]]
        self.profiles = profiles

    def find(self, setup: dict, parameter: str, game_version: str | None) -> ParameterLimits | None:
        metadata = setup.get("metadata", {})
        if not isinstance(metadata, dict) or metadata.get("source_format") != "ACC":
            return None
        matches = [profile for profile in self.profiles if (
            profile.car == metadata.get("car_name")
            and profile.game_version == game_version
            and profile.track_bop_type == metadata.get("track_bop_type")
            and profile.parameter == parameter
        )]
        # Perfis conflitantes também impedem recomendações numéricas.
        return matches[0] if len(matches) == 1 else None
