from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from app.models.contracts import ModelRequest
from .session import Session, Turn, TurnRole


@dataclass(frozen=True)
class ContextBrief:
    """Temporary working context for a single interaction.
    
    CRITICAL ARCHITECTURAL BOUNDARY:
    This is NOT permanent memory.
    This is NOT the long-term knowledge graph.
    This is NOT automatic retention or RAG indexing.
    This is solely an ephemeral, in-memory view constructed for a single model call.
    """
    user_request: str
    recent_turns: tuple[Turn, ...] = ()
    preferences: Mapping[str, Any] = field(default_factory=dict)
    constraints: tuple[str, ...] = ()
    evidence: tuple[Mapping[str, Any], ...] = ()
    request_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.user_request, str) or not self.user_request.strip():
            raise ValueError("ContextBrief must contain non-empty user_request text.")
        object.__setattr__(self, "recent_turns", tuple(self.recent_turns))
        object.__setattr__(self, "constraints", tuple(self.constraints))
        object.__setattr__(self, "evidence", tuple(self.evidence))

        for turn in self.recent_turns:
            if not isinstance(turn, Turn):
                raise ValueError(f"Every element in recent_turns must be a Turn, got {turn!r}.")
        for constraint in self.constraints:
            if not isinstance(constraint, str) or not constraint.strip():
                raise ValueError("Every constraint must be non-empty text.")
        for item in self.evidence:
            if not isinstance(item, Mapping):
                raise ValueError("Every evidence item must be a mapping.")
        if not isinstance(self.preferences, Mapping):
            raise ValueError("Preferences must be a mapping.")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("Metadata must be a mapping.")

    def render_prompt(self) -> str:
        sections: list[str] = []

        # 1. Operational Constraints
        if self.constraints:
            lines = ["Operational Constraints:"]
            for constraint in self.constraints:
                lines.append(f"- {constraint.strip()}")
            sections.append("\n".join(lines))

        # 2. Caller / User Preferences
        if self.preferences:
            lines = ["Active Preferences:"]
            for key, val in self.preferences.items():
                lines.append(f"- {key}: {val}")
            sections.append("\n".join(lines))

        # 3. Temporary Evidence / Reference Material (Working Context Only)
        if self.evidence:
            lines = ["Temporary Reference Evidence:"]
            for i, ev in enumerate(self.evidence, start=1):
                title = ev.get("title") or ev.get("source") or f"Source {i}"
                content = ev.get("content") or ev.get("text") or str(ev)
                lines.append(f"[{title}]:\n{content}")
            sections.append("\n".join(lines))

        # 4. Recent Conversation History
        if self.recent_turns:
            lines = ["Recent Conversation:"]
            for turn in self.recent_turns:
                prefix = "User" if turn.role == TurnRole.USER else "Assistant" if turn.role == TurnRole.ASSISTANT else "System"
                lines.append(f"{prefix}: {turn.text}")
            sections.append("\n".join(lines))

        # 5. Current Request
        sections.append(f"Current Request:\n{self.user_request.strip()}")

        return "\n\n".join(sections)

    def to_model_request(
        self,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        timeout_seconds: float = 60.0,
    ) -> ModelRequest:
        request_metadata = dict(self.metadata)
        if self.request_id:
            request_metadata["request_id"] = self.request_id

        return ModelRequest(
            text=self.render_prompt(),
            provider=provider,
            model=model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            metadata=request_metadata,
        )


class BriefBuilder:
    @staticmethod
    def build_brief(
        user_request: str,
        session: Session | None = None,
        max_turns: int | None = None,
        preferences: Mapping[str, Any] | None = None,
        constraints: Sequence[str] | None = None,
        evidence: Sequence[Mapping[str, Any]] | None = None,
        request_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ContextBrief:
        recent_turns: tuple[Turn, ...] = ()
        if session is not None:
            recent_turns = session.get_recent_turns(limit=max_turns)

        return ContextBrief(
            user_request=user_request,
            recent_turns=recent_turns,
            preferences=preferences or {},
            constraints=tuple(constraints or ()),
            evidence=tuple(evidence or ()),
            request_id=request_id,
            metadata=metadata or {},
        )
