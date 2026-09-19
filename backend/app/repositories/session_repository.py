import json
from datetime import UTC, datetime
from uuid import UUID

from app.database.sqlite import get_connection
from app.domain.models import CreateSessionRequest, SessionResponse, SetupVersionResponse
from app.setup_parsers import ParsedSetup


def _now() -> str:
    return datetime.now(UTC).isoformat()


class SessionRepository:
    def create(
        self,
        session_id: UUID,
        request: CreateSessionRequest,
        parsed_setup: ParsedSetup | None = None,
    ) -> SessionResponse:
        created_at = _now()
        initial_setup = parsed_setup.normalized if parsed_setup else {}
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
                INSERT INTO setup_versions (
                    session_id, version, setup_json, source, original_setup_json,
                    source_file_name, source_car_name, created_at
                )
                VALUES (?, 1, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(session_id),
                    json.dumps(initial_setup, ensure_ascii=False),
                    "importado" if parsed_setup else "vazio",
                    json.dumps(parsed_setup.original, ensure_ascii=False) if parsed_setup else None,
                    request.setup_file.filename if request.setup_file else None,
                    parsed_setup.source_car_name if parsed_setup else None,
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
            has_setup=parsed_setup is not None,
            created_at=datetime.fromisoformat(created_at),
        )

    def get(self, session_id: UUID) -> SessionResponse | None:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT sessions.*,
                    EXISTS(
                        SELECT 1 FROM setup_versions
                        WHERE setup_versions.session_id = sessions.id
                          AND setup_versions.source != 'vazio'
                    ) AS has_setup
                FROM sessions WHERE sessions.id = ?
                """,
                (str(session_id),),
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
            has_setup=bool(row["has_setup"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_current_setup(self, session_id: UUID) -> SetupVersionResponse:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT version, setup_json, source, source_file_name, source_car_name, created_at
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
            source_file_name=row["source_file_name"],
            source_car_name=row["source_car_name"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_setup_history(self, session_id: UUID) -> list[SetupVersionResponse]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT version, setup_json, source, source_file_name, source_car_name, created_at
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
                source_file_name=row["source_file_name"],
                source_car_name=row["source_car_name"],
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
