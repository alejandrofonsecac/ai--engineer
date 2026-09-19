from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Simulator(StrEnum):
    ACC = "ACC"
    IRACING = "iRacing"


class SessionType(StrEnum):
    PRACTICE = "Treino"
    HOTLAP = "Hotlap"
    QUALIFYING = "Classificação"
    RACE = "Corrida"
    SETUP_DEVELOPMENT = "Desenvolvimento de setup"


class SetupChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter: str = Field(min_length=1, max_length=100)
    current_value: str = Field(min_length=1, max_length=100)
    recommended_adjustment: str = Field(min_length=1, max_length=160)
    rationale: str = Field(min_length=1, max_length=500)
    positive_effects: list[str] = Field(min_length=1, max_length=3)
    negative_effects: list[str] = Field(min_length=1, max_length=3)
    menu: str | None = None
    limits_note: str | None = None

    @field_validator("current_value", "recommended_adjustment", mode="before")
    @classmethod
    def stringify_values(cls, value: Any) -> Any:
        return str(value) if isinstance(value, (int, float)) else value


class TestPlan(BaseModel):
    laps: int = Field(ge=3, le=10)
    focus: list[str] = Field(min_length=1, max_length=5)


class EngineerRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnosis: str = Field(min_length=1, max_length=1000)
    confidence: str = Field(pattern="^(baixa|média|alta)$")
    changes: list[SetupChange] = Field(default_factory=list, max_length=5)
    why: str = Field(min_length=1, max_length=1200)
    trade_offs: list[str] = Field(default_factory=list, max_length=5)
    test_plan: TestPlan | None = None
    clarification_question: str | None = Field(default=None, max_length=500)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"media": "média", "MEDIA": "média"}.get(value, value.lower())
        return value

    @model_validator(mode="after")
    def validate_recommendation(self) -> "EngineerRecommendation":
        if self.changes and (not self.test_plan or not self.trade_offs):
            raise ValueError("Alterações exigem plano de teste e trade-offs.")
        names = [change.parameter for change in self.changes]
        if len(names) != len(set(names)):
            raise ValueError("Parâmetros duplicados na recomendação.")
        return self


class AdjustmentChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # A lista válida vem de available_adjustments. Não restringir por enum aqui:
    # isso faria uma pergunta sobre um parâmetro novo falhar antes do guard.
    parameter: str = Field(min_length=1, max_length=80)
    direction: str = Field(min_length=1, max_length=20)
    # O guard permite somente 1 ou 2 cliques quando existir limite verificado.
    clicks: int = Field(default=1, ge=1, le=10)


class RecommendationDraft(BaseModel):
    """O modelo escolhe direção e intensidade; o backend valida o alvo e os efeitos."""

    model_config = ConfigDict(extra="forbid")
    diagnosis: str = Field(min_length=1, max_length=1000)
    confidence: str = Field(default="baixa", min_length=1, max_length=30)
    choices: list[AdjustmentChoice] = Field(default_factory=list, max_length=5)
    clarification_question: str | None = Field(default=None, max_length=500)

class SetupFileRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content: dict[str, Any]

    @field_validator("filename")
    @classmethod
    def require_json_file(cls, filename: str) -> str:
        if not filename.lower().endswith(".json"):
            raise ValueError("O setup do ACC deve ser um arquivo JSON.")
        return filename

    @model_validator(mode="after")
    def limit_file_size(self) -> "SetupFileRequest":
        import json

        if len(json.dumps(self.content, ensure_ascii=False).encode("utf-8")) > 1_000_000:
            raise ValueError("O arquivo de setup excede o limite de 1 MB.")
        return self


class CreateSessionRequest(BaseModel):
    simulator: Simulator
    car: str = Field(min_length=2, max_length=120)
    track: str = Field(min_length=2, max_length=120)
    session_type: SessionType
    setup_file: SetupFileRequest | None = None


class SessionResponse(BaseModel):
    id: UUID
    simulator: Simulator
    car: str
    track: str
    session_type: SessionType
    current_setup_version: int
    has_setup: bool = False
    created_at: datetime


class SetupVersionResponse(BaseModel):
    version: int
    setup: dict[str, Any]
    created_at: datetime
    source: str
    source_file_name: str | None = None
    source_car_name: str | None = None


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    content: str = Field(min_length=1, max_length=1200)


class StoredMessageResponse(BaseModel):
    role: str
    content: str


class ChatMessageResponse(BaseModel):
    session_id: UUID
    driver_message: str
    engineer_message: str
    recommendation: EngineerRecommendation | None = None


class LLMHealthResponse(BaseModel):
    available: bool
    provider: str = "ollama"
    model: str
    detail: str
