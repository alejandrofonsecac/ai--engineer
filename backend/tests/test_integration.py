import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.ai.ollama_provider import OllamaProvider
from app.ai.provider import LLMMessage, LLMResponseError, LLMTimeoutError, LLMUnavailableError
from app.api.dependencies import get_engineer_service
from app.config import Settings, get_settings
from app.domain.models import EngineerRecommendation
from app.main import app

REPLY = {
    "diagnosis": "Instabilidade na saída.",
    "confidence": "baixa", "changes": [],
    "why": "Precisamos identificar a fase da perda de aderência.",
    "trade_offs": [], "test_plan": None,
    "clarification_question": "A traseira escapa antes ou depois de acelerar?",
}
DRAFT_REPLY = {
    "diagnosis": "Instabilidade na saída.", "confidence": "baixa", "choices": [],
    "clarification_question": "A traseira escapa antes ou depois de acelerar?",
}

ACC_SETUP = {
    "carName": "ford_mustang_gt3",
    "basicSetup": {
        "tyres": {"tyreCompound": 0, "tyrePressure": [48, 48, 55, 55]},
        "alignment": {"camber": [0, 0, 0, 0], "toe": [9, 9, 15, 15]},
        "electronics": {"tC1": 3, "tC2": 3, "abs": 2},
        "strategy": {"fuel": 60, "nPitStops": 0},
    },
    "advancedSetup": {
        "mechanicalBalance": {"aRBFront": 5, "aRBRear": 2},
        "dampers": {"bumpSlow": [5, 5, 5, 5]},
        "aeroBalance": {"rideHeight": [0, 11, 10, 18], "rearWing": 6},
        "drivetrain": {"preload": 6},
    },
    "trackBopType": 35,
}

def run(coroutine):
    return asyncio.run(coroutine)


def test_provider_payload_and_health():
    requests = []
    def handle(request):
        requests.append(request)
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen2.5:3b"}]})
        return httpx.Response(200, json={"done": True, "message": {"content": json.dumps(REPLY)}})
    provider = OllamaProvider(Settings(_env_file=None), httpx.MockTransport(handle))
    assert run(provider.is_available())[0]
    schema = {"type": "object", "properties": {"diagnosis": {"type": "string"}}}
    run(provider.chat([LLMMessage("user", "teste")], response_schema=schema))
    payload = json.loads(requests[-1].content)
    assert payload["model"] == "qwen2.5:3b"
    assert payload["stream"] is False
    assert payload["keep_alive"] == "5m"
    assert payload["format"] == schema
    assert payload["options"] == {"temperature": 0.2, "num_ctx": 4096, "num_predict": 700}


@pytest.mark.parametrize("body", [
    {"done": True, "done_reason": "length", "message": {"content": "{}"}},
    {"done": True, "message": {}}, [],
])
def test_malformed_or_truncated_provider_response(body):
    provider = OllamaProvider(Settings(_env_file=None), httpx.MockTransport(
        lambda _: httpx.Response(200, json=body)))
    with pytest.raises(LLMResponseError):
        run(provider.chat([]))


def test_missing_model_and_timeout():
    missing = OllamaProvider(Settings(_env_file=None), httpx.MockTransport(
        lambda _: httpx.Response(404)))
    with pytest.raises(LLMUnavailableError, match="pull"):
        run(missing.chat([]))
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)
    slow = OllamaProvider(Settings(_env_file=None), httpx.MockTransport(timeout))
    with pytest.raises(LLMTimeoutError):
        run(slow.chat([]))


def test_more_than_five_changes_are_rejected():
    change = {
        "parameter": "wing", "current_value": "8",
        "recommended_adjustment": "reduzir", "rationale": "teste",
        "positive_effects": ["menos arrasto"],
        "negative_effects": ["menos estabilidade"],
    }
    with pytest.raises(ValidationError):
        EngineerRecommendation.model_validate({
            **REPLY, "changes": [
                {**change, "parameter": f"parameter-{index}"} for index in range(6)
            ],
            "trade_offs": ["compromisso"],
            "test_plan": {"laps": 5, "focus": ["reta"]},
        })


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VRE_DATABASE_PATH", str(tmp_path / "sessions.db"))
    get_settings.cache_clear()
    get_engineer_service.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()
    get_engineer_service.cache_clear()


def test_api_persistence_failure_and_real_contract(client):
    from app.ai.context_builder import EngineerContextBuilder
    from app.repositories.session_repository import SessionRepository
    from app.services.engineer_service import EngineerService
    from app.services.session_service import SessionService
    from app.services.knowledge_service import KnowledgeService

    class FakeProvider:
        fail = False
        changes = False
        async def chat(self, messages, response_schema=None):
            assert "iRacing" in messages[1].content
            assert messages[-1].content == "Traseira solta"
            assert response_schema["type"] == "object"
            if self.fail:
                raise LLMTimeoutError("Teste de timeout")
            if self.changes:
                return json.dumps({**DRAFT_REPLY, "choices": [{
                    "parameter": "rear_wing", "direction": "decrease",
                }]})
            return json.dumps(DRAFT_REPLY)

    repo = SessionRepository()
    provider = FakeProvider()
    service = EngineerService(repo, SessionService(repo), EngineerContextBuilder(KnowledgeService()), provider)
    app.dependency_overrides[get_engineer_service] = lambda: service
    try:
        response = client.post("/api/v1/sessions", json={
            "simulator": "iRacing", "car": "BMW M4 GT3", "track": "Monza", "session_type": "Treino",
        })
        assert response.status_code == 201
        session_id = response.json()["id"]
        url = f"/api/v1/sessions/{session_id}/messages"
        assert client.post(url, json={"content": "   "}).status_code == 422
        assert client.get(f"/api/v1/sessions/{uuid4()}").status_code == 404
        provider.fail = True
        assert client.post(url, json={"content": "Traseira solta"}).status_code == 504
        assert client.get(url).json() == []
        provider.fail = False
        provider.changes = True
        changed = client.post(url, json={"content": "Traseira solta"})
        assert changed.status_code == 200
        assert "Diagnóstico" in changed.json()["engineer_message"]
        provider.changes = False
        sent = client.post(url, json={"content": "Traseira solta"})
        assert sent.status_code == 200
        assert "Importe" in sent.json()["engineer_message"]
        assert [m["role"] for m in client.get(url).json()] == [
            "user", "assistant", "user", "assistant",
        ]
        assert len(client.get(f"/api/v1/sessions/{session_id}/setup/history").json()) == 1
    finally:
        app.dependency_overrides.clear()


def test_acc_setup_is_parsed_and_persisted_with_session(client):
    response = client.post("/api/v1/sessions", json={
        "simulator": "ACC",
        "car": "Ford Mustang GT3",
        "track": "Barcelona",
        "session_type": "Desenvolvimento de setup",
        "setup_file": {"filename": "teste.json", "content": ACC_SETUP},
    })

    assert response.status_code == 201
    assert response.json()["has_setup"] is True
    session_id = response.json()["id"]
    history = client.get(f"/api/v1/sessions/{session_id}/setup/history").json()
    assert len(history) == 1
    assert history[0]["source"] == "importado"
    assert history[0]["source_file_name"] == "teste.json"
    assert history[0]["source_car_name"] == "ford_mustang_gt3"
    assert history[0]["setup"]["aero"]["rearWing"] == 6
    assert history[0]["setup"]["mechanical_grip"]["drivetrain"]["preload"] == 6

    from app.database.sqlite import get_connection
    with get_connection() as connection:
        stored = connection.execute(
            "SELECT original_setup_json FROM setup_versions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    assert json.loads(stored["original_setup_json"]) == ACC_SETUP


def test_invalid_or_unsupported_setup_is_rejected_without_creating_session(client):
    invalid = client.post("/api/v1/sessions", json={
        "simulator": "ACC", "car": "Ford Mustang GT3", "track": "Barcelona",
        "session_type": "Treino",
        "setup_file": {"filename": "incompleto.json", "content": {"carName": "ford_mustang_gt3"}},
    })
    assert invalid.status_code == 422
    assert "basicSetup" in invalid.json()["detail"]

    unsupported = client.post("/api/v1/sessions", json={
        "simulator": "iRacing", "car": "BMW M4 GT3", "track": "Monza",
        "session_type": "Treino",
        "setup_file": {"filename": "teste.json", "content": ACC_SETUP},
    })
    assert unsupported.status_code == 422


def test_bounded_recommendation_saved_without_editing_setup(client, monkeypatch):
    class Provider:
        async def chat(self, messages, response_schema=None):
            assert "choices" in response_schema["properties"]
            assert '"value_in_file":3' in messages[1].content
            assert '"max":11' in messages[1].content
            return json.dumps({**DRAFT_REPLY, "choices": [
                {"parameter": "traction_control", "direction": "increase"},
                {"parameter": "rear_anti_roll_bar", "direction": "decrease"},
            ]})

    monkeypatch.setenv("VRE_ACC_GAME_VERSION", "1.10.3")
    get_settings.cache_clear()
    monkeypatch.setattr("app.api.dependencies.get_ollama_provider", lambda: Provider())
    created = client.post("/api/v1/sessions", json={
        "simulator": "ACC", "car": "ford_mustang_gt3", "track": "Barcelona",
        "session_type": "Treino", "setup_file": {"filename": "teste.json", "content": ACC_SETUP},
    })
    session_id = created.json()["id"]
    setup_url = f"/api/v1/sessions/{session_id}/setup/history"
    before = client.get(setup_url).json()
    message_url = f"/api/v1/sessions/{session_id}/messages"
    answer = client.post(message_url, json={"content": "A traseira escapa quando acelero. Perco velocidade final."})
    assert answer.status_code == 200
    text = answer.json()["engineer_message"]
    assert "3 → 4" in text and "2 → 1" in text
    assert "Pode piorar:" in text
    assert client.get(message_url).json()[-1]["content"] == text
    assert client.get(setup_url).json() == before


def test_invalid_draft_is_retried_once_before_returning_an_error(client):
    class Provider:
        def __init__(self):
            self.calls = 0

        async def chat(self, messages, response_schema=None):
            self.calls += 1
            if self.calls == 1:
                return "resposta sem JSON"
            assert "resposta anterior" in messages[-1].content
            return json.dumps(DRAFT_REPLY)

    from app.ai.context_builder import EngineerContextBuilder
    from app.repositories.session_repository import SessionRepository
    from app.services.engineer_service import EngineerService
    from app.services.knowledge_service import KnowledgeService
    from app.services.session_service import SessionService

    provider = Provider()
    repo = SessionRepository()
    service = EngineerService(repo, SessionService(repo), EngineerContextBuilder(KnowledgeService()), provider)
    app.dependency_overrides[get_engineer_service] = lambda: service
    try:
        created = client.post("/api/v1/sessions", json={
            "simulator": "iRacing", "car": "BMW M4 GT3", "track": "Monza", "session_type": "Treino",
        })
        response = client.post(
            f"/api/v1/sessions/{created.json()['id']}/messages",
            json={"content": "A traseira está solta."},
        )
        assert response.status_code == 200
        assert provider.calls == 2
    finally:
        app.dependency_overrides.clear()
