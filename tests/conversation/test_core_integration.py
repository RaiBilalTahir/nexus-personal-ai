import unittest

from app.conversation.commands import (
    CommandIntent,
    NexusCommand,
    ResponseStatus,
)
from app.conversation.engine import ConversationEngine
from app.conversation.session import SessionStore
from app.core import nexus_core
from app.models.contracts import ModelRequest, ModelResult
from app.models.gateway import ModelGateway


class EchoMockProvider:
    def __init__(self):
        self.last_request = None

    @property
    def provider_name(self):
        return "echo_mock"

    def generate(self, request: ModelRequest) -> ModelResult:
        self.last_request = request
        # Return structured echo response
        return ModelResult(
            success=True,
            provider="echo_mock",
            model="echo-v1",
            text=f"Echo reply to: {request.text[:30]}...",
        )


class CoreIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.provider = EchoMockProvider()
        self.gateway = ModelGateway(
            {"echo_mock": self.provider},
            default_provider="echo_mock",
            default_model="echo-v1",
        )
        self.session_store = SessionStore()
        # Initialize an isolated engine for the tests
        self.engine = ConversationEngine(
            gateway=self.gateway,
            session_store=self.session_store,
        )

    def test_execute_command_via_core(self):
        cmd = NexusCommand(
            text="How does an operating system manage memory?",
            session_id="core_sess_1",
            intent=CommandIntent.CONVERSATION,
            constraints=("Use concise explanations.",),
        )

        response = nexus_core.execute_command(cmd, engine=self.engine)

        self.assertTrue(response.is_success)
        self.assertEqual(response.status, ResponseStatus.SUCCESS)
        self.assertEqual(response.session_id, "core_sess_1")
        self.assertIn("Echo reply to:", response.text or "")

        # Verify the model received the prompt containing constraints
        self.assertIsNotNone(self.provider.last_request)
        self.assertIn("Use concise explanations.", self.provider.last_request.text or "")
        self.assertIn("How does an operating system manage memory?", self.provider.last_request.text or "")

    def test_send_chat_message_multi_turn(self):
        session_id = "core_sess_multi"

        # Turn 1
        r1 = nexus_core.send_chat_message(
            "First question",
            session_id=session_id,
            engine=self.engine,
        )
        self.assertTrue(r1.is_success)

        # Turn 2
        r2 = nexus_core.send_chat_message(
            "Second question",
            session_id=session_id,
            engine=self.engine,
        )
        self.assertTrue(r2.is_success)

        # Verify session has both turns
        session = self.session_store.get_session(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session.turn_count, 4)  # 2 user + 2 assistant turns

        # Check prompt of second request included first turn in conversation history
        self.assertIn("Recent Conversation:", self.provider.last_request.text or "")
        self.assertIn("User: First question", self.provider.last_request.text or "")

    def test_session_reset_via_core(self):
        session_id = "core_sess_reset"
        nexus_core.send_chat_message("Hello", session_id=session_id, engine=self.engine)

        session = self.session_store.get_session(session_id)
        self.assertEqual(session.turn_count, 2)

        reset_success = nexus_core.reset_session(session_id, engine=self.engine)
        self.assertTrue(reset_success)
        self.assertEqual(session.turn_count, 0)

    def test_foundation_behavior_preserved(self):
        # Verify core properties and existing foundation functions remain operational
        self.assertEqual(nexus_core.NEXUS_NAME, "Nexus")
        self.assertEqual(nexus_core.NEXUS_VERSION, "1.1.1")
        self.assertTrue(nexus_core.feature_enabled("process_notes"))
        self.assertFalse(nexus_core.feature_enabled("pc_control"))


if __name__ == "__main__":
    unittest.main()
