from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, model_validator


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
    parameter: str = Field(min_length=1, max_length=100)
    previous_value: str = Field(min_length=1, max_length=80)
    proposed_value: str = Field(min_length=1, max_length=80)
    rationale: str = Field(min_length=1, max_length=500)


class TestPlan(BaseModel):
    laps: int = Field(ge=3, le=10)
    focus: list[str] = Field(min_length=1, max_length=5)


class EngineerRecommendation(BaseModel):
    diagnosis: str = Field(min_length=1, max_length=1000)
    confidence: str = Field(pattern="^(baixa|média|alta)$")
    changes: list[SetupChange] = Field(default_factory=list, max_length=5)
    why: str = Field(min_length=1, max_length=1200)
    trade_offs: list[str] = Field(default_factory=list, max_length=5)
    test_plan: TestPlan | None = None
    clarification_question: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_recommendation(self) -> "EngineerRecommendation":
        if self.changes and (not self.test_plan or not self.trade_offs):
            raise ValueError("Alterações exigem plano de teste e trade-offs.")
        names = [change.parameter for change in self.changes]
        if len(names) != len(set(names)):
            raise ValueError("Parâmetros duplicados na recomendação.")
        return self

class CreateSessionRequest(BaseModel):
    simulator: Simulator
    car: str = Field(min_length=2, max_length=120)
    track: str = Field(min_length=2, max_length=120)
    session_type: SessionType
    normalized_setup: dict[str, Any] | None = None


class SessionResponse(BaseModel):
    id: UUID
    simulator: Simulator
    car: str
    track: str
    session_type: SessionType
    current_setup_version: int
    created_at: datetime


class SetupVersionResponse(BaseModel):
    version: int
    setup: dict[str, Any]
    created_at: datetime
    source: str


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
