from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
import uuid


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CommandIntent(str, Enum):
    CONVERSATION = "conversation"
    QUERY = "query"
    ACTION = "action"
    SYSTEM = "system"


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    INVALID_REQUEST = "invalid_request"
    MODEL_ERROR = "model_error"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class NexusError:
    category: str
    message: str
    code: str
    retryable: bool = False
    detail: str | None = None

    def __post_init__(self):
        if not isinstance(self.category, str) or not self.category.strip():
            raise ValueError("Error category must be non-empty text.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("Error message must be non-empty text.")
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("Error code must be non-empty text.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "message": self.message,
            "code": self.code,
            "retryable": self.retryable,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class NexusCommand:
    """Represents a validated, typed command presented to the Nexus Core."""
    text: str
    session_id: str | None = None
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    intent: CommandIntent = CommandIntent.CONVERSATION
    preferences: Mapping[str, Any] = field(default_factory=dict)
    constraints: tuple[str, ...] = ()
    evidence: tuple[Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self):
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("Command text must be non-empty text.")
        if not isinstance(self.intent, CommandIntent):
            raise ValueError(f"Intent must be a CommandIntent enum member, got {self.intent!r}.")
        if self.session_id is not None and not isinstance(self.session_id, str):
            raise ValueError("session_id must be a string or None.")
        object.__setattr__(self, "constraints", tuple(self.constraints))
        object.__setattr__(self, "evidence", tuple(self.evidence))

        for c in self.constraints:
            if not isinstance(c, str) or not c.strip():
                raise ValueError("Constraints must be non-empty strings.")
        for e in self.evidence:
            if not isinstance(e, Mapping):
                raise ValueError("Evidence items must be mappings.")
        if not isinstance(self.preferences, Mapping):
            raise ValueError("Preferences must be a mapping.")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("Metadata must be a mapping.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "text": self.text,
            "intent": self.intent.value,
            "preferences": dict(self.preferences),
            "constraints": list(self.constraints),
            "evidence": [dict(e) for e in self.evidence],
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class NexusResponse:
    """Represents the structured execution response from Nexus Core."""
    request_id: str
    response_id: str
    session_id: str | None
    status: ResponseStatus
    text: str | None = None
    error: NexusError | None = None
    latency_ms: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self):
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError("request_id must be non-empty text.")
        if not isinstance(self.response_id, str) or not self.response_id.strip():
            raise ValueError("response_id must be non-empty text.")
        if not isinstance(self.status, ResponseStatus):
            raise ValueError(f"status must be a ResponseStatus enum member, got {self.status!r}.")
        if self.status == ResponseStatus.SUCCESS:
            if self.error is not None:
                raise ValueError("Successful response must not have an error.")
            if self.text is None:
                raise ValueError("Successful response must include text.")
        else:
            if self.error is None:
                raise ValueError("Failed response must include a NexusError.")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("Metadata must be a mapping.")

    @property
    def is_success(self) -> bool:
        return self.status == ResponseStatus.SUCCESS

    @classmethod
    def successful(
        cls,
        request_id: str,
        session_id: str | None,
        text: str,
        response_id: str | None = None,
        latency_ms: float | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> NexusResponse:
        return cls(
            request_id=request_id,
            response_id=response_id or f"resp_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            status=ResponseStatus.SUCCESS,
            text=text,
            latency_ms=latency_ms,
            metadata=metadata or {},
        )

    @classmethod
    def failure(
        cls,
        request_id: str,
        session_id: str | None,
        status: ResponseStatus,
        error: NexusError,
        response_id: str | None = None,
        latency_ms: float | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> NexusResponse:
        return cls(
            request_id=request_id,
            response_id=response_id or f"resp_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            status=status,
            error=error,
            latency_ms=latency_ms,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "response_id": self.response_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "text": self.text,
            "error": self.error.to_dict() if self.error else None,
            "latency_ms": self.latency_ms,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }
