import json
from datetime import UTC, datetime
from uuid import UUID

from app.database.sqlite import get_connection
from app.domain.models import CreateSessionRequest, SessionResponse, SetupVersionResponse


def _now() -> str:
    return datetime.now(UTC).isoformat()


class SessionRepository:
    def create(self, session_id: UUID, request: CreateSessionRequest) -> SessionResponse:
        created_at = _now()
        initial_setup = request.normalized_setup or {}
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO sessions
                    (id, simulator, car, track, session_type, current_setup_version, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    str(session_id),
                    request.simulator.value,
                    request.car,
                    request.track,
                    request.session_type.value,
                    created_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO setup_versions (session_id, version, setup_json, source, created_at)
                VALUES (?, 1, ?, ?, ?)
                """,
                (
                    str(session_id),
                    json.dumps(initial_setup, ensure_ascii=False),
                    "importado" if request.normalized_setup else "vazio",
                    created_at,
                ),
            )
        return SessionResponse(
            id=session_id,
            simulator=request.simulator,
            car=request.car,
            track=request.track,
            session_type=request.session_type,
            current_setup_version=1,
            created_at=datetime.fromisoformat(created_at),
        )

    def get(self, session_id: UUID) -> SessionResponse | None:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE id = ?", (str(session_id),)
            ).fetchone()
        if row is None:
            return None
        return SessionResponse(
            id=UUID(row["id"]),
            simulator=row["simulator"],
            car=row["car"],
            track=row["track"],
            session_type=row["session_type"],
            current_setup_version=row["current_setup_version"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_current_setup(self, session_id: UUID) -> SetupVersionResponse:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT version, setup_json, source, created_at
                FROM setup_versions
                WHERE session_id = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (str(session_id),),
            ).fetchone()
        if row is None:
            raise LookupError("Nenhuma versão de setup encontrada para a sessão.")
        return SetupVersionResponse(
            version=row["version"],
            setup=json.loads(row["setup_json"]),
            source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_setup_history(self, session_id: UUID) -> list[SetupVersionResponse]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT version, setup_json, source, created_at
                FROM setup_versions
                WHERE session_id = ?
                ORDER BY version ASC
                """,
                (str(session_id),),
            ).fetchall()
        return [
            SetupVersionResponse(
                version=row["version"],
                setup=json.loads(row["setup_json"]),
                source=row["source"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def add_exchange(self, session_id: UUID, user: str, assistant: str) -> None:
        with get_connection() as connection:
            connection.executemany(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                [
                    (str(session_id), "user", user, _now()),
                    (str(session_id), "assistant", assistant, _now()),
                ],
            )

    def get_messages(self, session_id: UUID, limit: int = 12) -> list[dict[str, str]]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT role, content FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(session_id), limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]
