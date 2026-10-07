from types import SimpleNamespace
import unittest

from app.conversation.commands import (
    CommandIntent,
    NexusCommand,
    ResponseStatus,
)
from app.conversation.engine import ConversationEngine, RetryPolicy
from app.conversation.session import SessionStore, TurnRole
from app.models.contracts import (
    ErrorCategory,
    ModelError,
    ModelRequest,
    ModelResult,
)
from app.models.gateway import ModelGateway


class MockProvider:
    def __init__(self, responses):
        # responses can be a list of ModelResults to yield sequentially
        self.responses = list(responses)
        self.calls = []

    @property
    def provider_name(self):
        return "mock"

    def generate(self, request: ModelRequest) -> ModelResult:
        self.calls.append(request)
        if self.responses:
            return self.responses.pop(0)
        return ModelResult(
            success=True,
            provider="mock",
            model="mock-model",
            text="Default response",
        )


class ConversationEngineTests(unittest.TestCase):
    def setUp(self):
        self.session_store = SessionStore()

    def test_successful_execution(self):
        mock_provider = MockProvider([
            ModelResult(
                success=True,
                provider="mock",
                model="mock-model",
                text="Binary code consists of 0s and 1s.",
            )
        ])
        gateway = ModelGateway({"mock": mock_provider}, default_provider="mock", default_model="mock-model")
        engine = ConversationEngine(gateway=gateway, session_store=self.session_store)

        cmd = NexusCommand(text="What is binary code?", session_id="sess_binary")
        response = engine.execute_command(cmd)

        self.assertTrue(response.is_success)
        self.assertEqual(response.status, ResponseStatus.SUCCESS)
        self.assertEqual(response.text, "Binary code consists of 0s and 1s.")
        self.assertEqual(response.session_id, "sess_binary")
        self.assertEqual(response.request_id, cmd.request_id)

        # Verify session state
        session = self.session_store.get_session("sess_binary")
        self.assertIsNotNone(session)
        self.assertEqual(session.turn_count, 2)
        self.assertEqual(session.turns[0].role, TurnRole.USER)
        self.assertEqual(session.turns[0].text, "What is binary code?")
        self.assertEqual(session.turns[1].role, TurnRole.ASSISTANT)
        self.assertEqual(session.turns[1].text, "Binary code consists of 0s and 1s.")
        self.assertEqual(session.turns[1].response_id, response.response_id)

    def test_non_retryable_provider_failure(self):
        mock_provider = MockProvider([
            ModelResult.failure(
                provider="mock",
                model="mock-model",
                error=ModelError(
                    category=ErrorCategory.MISSING_CREDENTIALS,
                    retryable=False,
                    detail="No API key provided",
                ),
            )
        ])
        gateway = ModelGateway({"mock": mock_provider}, default_provider="mock")
        engine = ConversationEngine(gateway=gateway, session_store=self.session_store)

        cmd = NexusCommand(text="Test question", session_id="sess_fail")
        response = engine.execute_command(cmd)

        self.assertFalse(response.is_success)
        self.assertEqual(response.status, ResponseStatus.MODEL_ERROR)
        self.assertEqual(response.error.category, "missing_credentials")
        self.assertFalse(response.error.retryable)

        # Called exactly once, no retries
        self.assertEqual(len(mock_provider.calls), 1)

        # User turn is preserved, but no assistant turn was recorded
        session = self.session_store.get_session("sess_fail")
        self.assertEqual(session.turn_count, 1)
        self.assertEqual(session.turns[0].role, TurnRole.USER)

    def test_transient_retry_succeeds_on_second_attempt(self):
        mock_provider = MockProvider([
            ModelResult.failure(
                provider="mock",
                model="mock-model",
                error=ModelError(
                    category=ErrorCategory.TIMEOUT,
                    retryable=True,
                    detail="Gateway timeout",
                ),
            ),
            ModelResult(
                success=True,
                provider="mock",
                model="mock-model",
                text="Recovered answer after timeout.",
            ),
        ])
        gateway = ModelGateway({"mock": mock_provider}, default_provider="mock")
        policy = RetryPolicy(max_retries=2, backoff_seconds=0.0)
        engine = ConversationEngine(gateway=gateway, session_store=self.session_store, retry_policy=policy)

        cmd = NexusCommand(text="Retry question", session_id="sess_retry")
        response = engine.execute_command(cmd)

        self.assertTrue(response.is_success)
        self.assertEqual(response.text, "Recovered answer after timeout.")
        self.assertEqual(len(mock_provider.calls), 2)
        self.assertEqual(response.metadata.get("attempts"), 2)

        # CRITICAL SAFETY CHECK:
        # Session must only have ONE user turn and ONE assistant turn!
        # The retry must NEVER duplicate user turns.
        session = self.session_store.get_session("sess_retry")
        self.assertEqual(session.turn_count, 2)
        self.assertEqual(session.turns[0].role, TurnRole.USER)
        self.assertEqual(session.turns[0].text, "Retry question")
        self.assertEqual(session.turns[1].role, TurnRole.ASSISTANT)
        self.assertEqual(session.turns[1].text, "Recovered answer after timeout.")

    def test_retry_exhaustion_returns_model_error(self):
        mock_provider = MockProvider([
            ModelResult.failure(
                provider="mock",
                model="mock-model",
                error=ModelError(category=ErrorCategory.RATE_LIMITED, retryable=True, detail="429 quota"),
            ),
            ModelResult.failure(
                provider="mock",
                model="mock-model",
                error=ModelError(category=ErrorCategory.RATE_LIMITED, retryable=True, detail="429 quota"),
            ),
            ModelResult.failure(
                provider="mock",
                model="mock-model",
                error=ModelError(category=ErrorCategory.RATE_LIMITED, retryable=True, detail="429 quota"),
            ),
        ])
        gateway = ModelGateway({"mock": mock_provider}, default_provider="mock")
        policy = RetryPolicy(max_retries=2, backoff_seconds=0.0)
        engine = ConversationEngine(gateway=gateway, session_store=self.session_store, retry_policy=policy)

        cmd = NexusCommand(text="Rate limited query", session_id="sess_quota")
        response = engine.execute_command(cmd)

        self.assertFalse(response.is_success)
        self.assertEqual(response.status, ResponseStatus.MODEL_ERROR)
        self.assertEqual(response.error.category, "rate_limited")
        # 1 initial + 2 retries = 3 calls
        self.assertEqual(len(mock_provider.calls), 3)

        # User turn preserved once
        session = self.session_store.get_session("sess_quota")
        self.assertEqual(session.turn_count, 1)

    def test_invalid_command_type_rejected(self):
        gateway = ModelGateway({}, default_provider="mock")
        engine = ConversationEngine(gateway=gateway, session_store=self.session_store)

        response = engine.execute_command("Not a command object")  # type: ignore
        self.assertFalse(response.is_success)
        self.assertEqual(response.status, ResponseStatus.INVALID_REQUEST)
        self.assertEqual(response.error.code, "invalid_command_type")


if __name__ == "__main__":
    unittest.main()
