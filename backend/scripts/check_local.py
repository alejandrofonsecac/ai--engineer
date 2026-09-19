"""Verificação manual: FastAPI -> serviço -> Ollama real, com banco temporário."""
import argparse
import json
import os
import tempfile
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", type=Path, help="Setup JSON opcional do ACC.")
    parser.add_argument(
        "--feedback",
        default="A traseira escapa quando acelero saindo das curvas lentas. O que devo observar?",
    )
    args = parser.parse_args()
    setup = None
    if args.setup:
        with args.setup.open(encoding="utf-8-sig") as file:
            setup = {"filename": args.setup.name, "content": json.load(file)}

    with tempfile.TemporaryDirectory(prefix="vre-smoke-") as directory:
        os.environ["VRE_DATABASE_PATH"] = str(Path(directory) / "smoke.db")
        from fastapi.testclient import TestClient
        from app.config import get_settings
        from app.main import app
        get_settings.cache_clear()
        with TestClient(app) as client:
            health = client.get("/api/v1/health/llm")
            print("IA local:", health.json(), flush=True)
            if not health.json()["available"]:
                raise SystemExit("Ollama/modelo indisponível.")
            session_request = {
                "simulator": "ACC",
                "car": setup["content"]["carName"] if setup else "Porsche 992 GT3 R",
                "track": "Nürburgring Nordschleife",
                "session_type": "Desenvolvimento de setup",
            }
            if setup:
                session_request["setup_file"] = setup
            session = client.post("/api/v1/sessions", json=session_request)
            session.raise_for_status()
            session_id = session.json()["id"]
            start = time.perf_counter()
            response = client.post(f"/api/v1/sessions/{session_id}/messages", json={
                "content": args.feedback,
            })
            print(f"Resposta HTTP {response.status_code}, {time.perf_counter() - start:.1f}s", flush=True)
            print(response.json(), flush=True)
            response.raise_for_status()
            history = client.get(f"/api/v1/sessions/{session_id}/messages")
            assert len(history.json()) == 2, "Conversa não foi persistida."
            print("OK: geração real e persistência verificadas em banco temporário.", flush=True)


if __name__ == "__main__":
    main()
