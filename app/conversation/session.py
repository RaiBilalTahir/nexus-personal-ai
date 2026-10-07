from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import threading
from typing import Any, Mapping
import uuid


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TurnRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class Turn:
    turn_id: str
    role: TurnRole
    text: str
    timestamp: str = field(default_factory=_utc_now_iso)
    request_id: str | None = None
    response_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.turn_id, str) or not self.turn_id.strip():
            raise ValueError("Turn ID must be non-empty text.")
        if not isinstance(self.role, TurnRole):
            raise ValueError(f"Role must be a TurnRole enum member, got {self.role!r}.")
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("Turn text must be non-empty text.")
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("Timestamp must be non-empty ISO text.")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("Metadata must be a mapping.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "role": self.role.value,
            "text": self.text,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "response_id": self.response_id,
            "metadata": dict(self.metadata),
        }


class Session:
    def __init__(
        self,
        session_id: str | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
        max_recent_turns: int = 10,
        metadata: Mapping[str, Any] | None = None,
    ):
        if session_id is not None and (not isinstance(session_id, str) or not session_id.strip()):
            raise ValueError("Session ID must be non-empty text if provided.")
        if max_recent_turns <= 0:
            raise ValueError("max_recent_turns must be greater than zero.")

        self.session_id: str = session_id.strip() if session_id else str(uuid.uuid4())
        self.created_at: str = created_at or _utc_now_iso()
        self.updated_at: str = updated_at or self.created_at
        self.max_recent_turns: int = max_recent_turns
        self.metadata: dict[str, Any] = dict(metadata or {})
        self._turns: list[Turn] = []
        self._lock = threading.RLock()

    @property
    def turns(self) -> tuple[Turn, ...]:
        with self._lock:
            return tuple(self._turns)

    @property
    def turn_count(self) -> int:
        with self._lock:
            return len(self._turns)

    def add_turn(self, turn: Turn) -> Turn:
        if not isinstance(turn, Turn):
            raise ValueError("Turn must be an instance of Turn.")
        with self._lock:
            self._turns.append(turn)
            self.updated_at = _utc_now_iso()
            return turn

    def add_user_turn(
        self,
        text: str,
        request_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Turn:
        turn = Turn(
            turn_id=f"turn_{uuid.uuid4().hex[:12]}",
            role=TurnRole.USER,
            text=text,
            timestamp=_utc_now_iso(),
            request_id=request_id,
            metadata=metadata or {},
        )
        return self.add_turn(turn)

    def add_assistant_turn(
        self,
        text: str,
        request_id: str | None = None,
        response_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Turn:
        turn = Turn(
            turn_id=f"turn_{uuid.uuid4().hex[:12]}",
            role=TurnRole.ASSISTANT,
            text=text,
            timestamp=_utc_now_iso(),
            request_id=request_id,
            response_id=response_id,
            metadata=metadata or {},
        )
        return self.add_turn(turn)

    def add_system_turn(
        self,
        text: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> Turn:
        turn = Turn(
            turn_id=f"turn_{uuid.uuid4().hex[:12]}",
            role=TurnRole.SYSTEM,
            text=text,
            timestamp=_utc_now_iso(),
            metadata=metadata or {},
        )
        return self.add_turn(turn)

    def get_recent_turns(self, limit: int | None = None) -> tuple[Turn, ...]:
        with self._lock:
            bound = self.max_recent_turns if limit is None or limit <= 0 else limit
            if not self._turns:
                return ()
            return tuple(self._turns[-bound:])

    def reset(self) -> None:
        with self._lock:
            self._turns.clear()
            self.updated_at = _utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "session_id": self.session_id,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "max_recent_turns": self.max_recent_turns,
                "turn_count": len(self._turns),
                "turns": [turn.to_dict() for turn in self._turns],
                "metadata": dict(self.metadata),
            }


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    def create_session(
        self,
        session_id: str | None = None,
        max_recent_turns: int = 10,
        metadata: Mapping[str, Any] | None = None,
    ) -> Session:
        with self._lock:
            if session_id and session_id in self._sessions:
                raise ValueError(f"Session with ID '{session_id}' already exists.")
            session = Session(
                session_id=session_id,
                max_recent_turns=max_recent_turns,
                metadata=metadata,
            )
            self._sessions[session.session_id] = session
            return session

    def get_session(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_or_create_session(
        self,
        session_id: str | None = None,
        max_recent_turns: int = 10,
    ) -> Session:
        with self._lock:
            if session_id and session_id in self._sessions:
                return self._sessions[session_id]
            return self.create_session(
                session_id=session_id,
                max_recent_turns=max_recent_turns,
            )

    def reset_session(self, session_id: str) -> Session | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                session.reset()
            return session

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def list_sessions(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._sessions.keys())

    def clear_all(self) -> None:
        with self._lock:
            self._sessions.clear()
