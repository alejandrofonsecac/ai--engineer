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
    run(provider.chat([LLMMessage("user", "teste")]))
    payload = json.loads(requests[-1].content)
    assert payload["model"] == "qwen2.5:3b"
    assert payload["stream"] is False
    assert payload["keep_alive"] == "5m"
    assert payload["options"] == {"temperature": 0.2, "num_ctx": 4096, "num_predict": 300}


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


@pytest.mark.parametrize("count", [6, 1])
def test_invalid_changes_rejected(count):
    change = {"parameter": "wing", "previous_value": "8", "proposed_value": "9", "rationale": "teste"}
    with pytest.raises(ValidationError):
        EngineerRecommendation.model_validate({**REPLY, "changes": [change] * count})


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
        async def chat(self, messages):
            assert "iRacing" in messages[1].content
            assert messages[-1].content == "Traseira solta"
            if self.fail:
                raise LLMTimeoutError("Teste de timeout")
            if self.changes:
                return json.dumps({**REPLY, "changes": [{
                    "parameter": "wing", "previous_value": "8", "proposed_value": "9", "rationale": "teste",
                }], "trade_offs": ["arrasto"], "test_plan": {"laps": 5, "focus": ["reta"]}})
            return json.dumps(REPLY)

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
        assert client.post(url, json={"content": "Traseira solta"}).status_code == 502
        assert client.get(url).json() == []
        provider.changes = False
        sent = client.post(url, json={"content": "Traseira solta"})
        assert sent.status_code == 200
        assert "antes ou depois" in sent.json()["engineer_message"]
        assert [m["role"] for m in client.get(url).json()] == ["user", "assistant"]
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
