from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


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
    content: str = Field(min_length=1, max_length=4000)


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
