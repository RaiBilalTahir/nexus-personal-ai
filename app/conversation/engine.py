from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Mapping
import uuid

from app.models.contracts import ErrorCategory, ModelError, ModelRequest, ModelResult
from app.models.gateway import ModelGateway
from .brief import BriefBuilder, ContextBrief
from .commands import (
    CommandIntent,
    NexusCommand,
    NexusError,
    NexusResponse,
    ResponseStatus,
)
from .session import Session, SessionStore, TurnRole


logger = logging.getLogger("nexus.conversation.engine")


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 2
    retryable_categories: tuple[ErrorCategory, ...] = (
        ErrorCategory.TIMEOUT,
        ErrorCategory.RATE_LIMITED,
        ErrorCategory.PROVIDER_UNAVAILABLE,
    )
    backoff_seconds: float = 0.0

    def __post_init__(self):
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative.")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds must be non-negative.")


class ConversationEngine:
    """Executes validated NexusCommands against session state and the ModelGateway.
    
    Guarantees:
    - User turns are appended exactly once prior to model interaction.
    - Transient retry loop executes solely against the ModelGateway without duplicating state.
    - Assistant turns are appended if and only if the model responds successfully.
    - Ephemeral ContextBrief is used for interaction and not retained as permanent memory.
    - Structured success and failure responses are returned.
    """

    def __init__(
        self,
        gateway: ModelGateway,
        session_store: SessionStore | None = None,
        retry_policy: RetryPolicy | None = None,
        default_max_recent_turns: int = 10,
    ):
        if gateway is None:
            raise ValueError("ModelGateway must be provided.")
        self._gateway = gateway
        self._session_store = session_store if session_store is not None else SessionStore()
        self._retry_policy = retry_policy if retry_policy is not None else RetryPolicy()
        self._default_max_recent_turns = default_max_recent_turns

    @property
    def gateway(self) -> ModelGateway:
        return self._gateway

    @property
    def session_store(self) -> SessionStore:
        return self._session_store

    @property
    def retry_policy(self) -> RetryPolicy:
        return self._retry_policy

    def execute_command(self, command: NexusCommand) -> NexusResponse:
        start_time = time.perf_counter()

        # 1. Validation
        if not isinstance(command, NexusCommand):
            return NexusResponse.failure(
                request_id=getattr(command, "request_id", "unknown_req"),
                session_id=getattr(command, "session_id", None),
                status=ResponseStatus.INVALID_REQUEST,
                error=NexusError(
                    category="invalid_request",
                    message="Command must be an instance of NexusCommand.",
                    code="invalid_command_type",
                    retryable=False,
                ),
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        try:
            # 2. Session Resolution
            session = self._session_store.get_or_create_session(
                session_id=command.session_id,
                max_recent_turns=self._default_max_recent_turns,
            )

            # 3. Record User Turn (Executed once, never duplicated on retry)
            user_turn = session.add_user_turn(
                text=command.text,
                request_id=command.request_id,
                metadata={"intent": command.intent.value},
            )

            # 4. Gather prior turns for temporary ContextBrief (excluding the newly added turn)
            all_recent = session.get_recent_turns(limit=self._default_max_recent_turns + 1)
            prior_turns = tuple(t for t in all_recent if t.turn_id != user_turn.turn_id)

            # 5. Construct Ephemeral Context Brief
            brief = ContextBrief(
                user_request=command.text,
                recent_turns=prior_turns,
                preferences=command.preferences,
                constraints=command.constraints,
                evidence=command.evidence,
                request_id=command.request_id,
                metadata=command.metadata,
            )

            # 6. Build Model Request
            model_request = brief.to_model_request(
                provider=self._gateway.default_provider,
                model=self._gateway.default_model,
            )

            # 7. Model Execution with Deterministic Retry
            attempts = 0
            model_result: ModelResult | None = None

            while attempts <= self._retry_policy.max_retries:
                attempts += 1
                model_result = self._gateway.generate(model_request)

                if model_result.success:
                    break

                err = model_result.error
                if (
                    err
                    and err.retryable
                    and err.category in self._retry_policy.retryable_categories
                    and attempts <= self._retry_policy.max_retries
                ):
                    logger.warning(
                        "Transient model error (%s). Retrying attempt %d of %d.",
                        err.category.value,
                        attempts,
                        self._retry_policy.max_retries,
                    )
                    if self._retry_policy.backoff_seconds > 0:
                        time.sleep(self._retry_policy.backoff_seconds * attempts)
                    continue

                break

            total_latency = (time.perf_counter() - start_time) * 1000

            # 8. Result Handling
            if model_result is not None and model_result.success:
                resp_id = f"resp_{uuid.uuid4().hex[:12]}"
                session.add_assistant_turn(
                    text=model_result.text or "",
                    request_id=command.request_id,
                    response_id=resp_id,
                    metadata={
                        "provider": model_result.provider,
                        "model": model_result.model,
                        "attempts": attempts,
                    },
                )

                return NexusResponse.successful(
                    request_id=command.request_id,
                    response_id=resp_id,
                    session_id=session.session_id,
                    text=model_result.text or "",
                    latency_ms=total_latency,
                    metadata={
                        "provider": model_result.provider,
                        "model": model_result.model,
                        "attempts": attempts,
                        "usage": dict(model_result.usage),
                    },
                )

            # Model Failure
            error_category = (
                model_result.error.category.value
                if model_result and model_result.error
                else "unknown_model_error"
            )
            error_detail = (
                model_result.error.detail
                if model_result and model_result.error
                else "Model generation returned no result"
            )
            retryable = (
                model_result.error.retryable
                if model_result and model_result.error
                else False
            )

            return NexusResponse.failure(
                request_id=command.request_id,
                session_id=session.session_id,
                status=ResponseStatus.MODEL_ERROR,
                error=NexusError(
                    category=error_category,
                    message=f"Model failure: {error_detail or error_category}",
                    code=error_category,
                    retryable=retryable,
                    detail=error_detail,
                ),
                latency_ms=total_latency,
                metadata={"attempts": attempts},
            )

        except Exception as exc:
            total_latency = (time.perf_counter() - start_time) * 1000
            logger.exception("Internal error during command execution: %s", exc)
            return NexusResponse.failure(
                request_id=command.request_id,
                session_id=getattr(command, "session_id", None),
                status=ResponseStatus.INTERNAL_ERROR,
                error=NexusError(
                    category="internal_error",
                    message=str(exc) or "Internal execution failure",
                    code="internal_exception",
                    retryable=False,
                    detail=type(exc).__name__,
                ),
                latency_ms=total_latency,
            )
