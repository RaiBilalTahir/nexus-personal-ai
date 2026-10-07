import unittest

from app.conversation.commands import (
    CommandIntent,
    NexusCommand,
    NexusError,
    NexusResponse,
    ResponseStatus,
)


class CommandResponseTests(unittest.TestCase):
    def test_command_creation_defaults(self):
        cmd = NexusCommand(text="Explain CPU registers")
        self.assertEqual(cmd.text, "Explain CPU registers")
        self.assertIsNone(cmd.session_id)
        self.assertTrue(cmd.request_id.startswith("req_"))
        self.assertEqual(cmd.intent, CommandIntent.CONVERSATION)
        self.assertEqual(cmd.preferences, {})
        self.assertEqual(cmd.constraints, ())
        self.assertEqual(cmd.evidence, ())

    def test_command_validation_rejections(self):
        with self.assertRaises(ValueError):
            NexusCommand(text="")
        with self.assertRaises(ValueError):
            NexusCommand(text="   ")
        with self.assertRaises(ValueError):
            NexusCommand(text="Valid", intent="invalid_intent")  # type: ignore

    def test_command_to_dict(self):
        cmd = NexusCommand(
            text="Test text",
            session_id="sess_123",
            request_id="req_456",
            intent=CommandIntent.QUERY,
            preferences={"mode": "test"},
            constraints=("no_write",),
            evidence=({"id": 1},),
        )
        d = cmd.to_dict()
        self.assertEqual(d["text"], "Test text")
        self.assertEqual(d["session_id"], "sess_123")
        self.assertEqual(d["request_id"], "req_456")
        self.assertEqual(d["intent"], "query")
        self.assertEqual(d["preferences"], {"mode": "test"})
        self.assertEqual(d["constraints"], ["no_write"])
        self.assertEqual(d["evidence"], [{"id": 1}])

    def test_response_successful_factory(self):
        resp = NexusResponse.successful(
            request_id="req_1",
            session_id="sess_1",
            text="Registers are fast storage locations inside the CPU.",
            latency_ms=125.5,
            metadata={"model": "gemini-3.8-flash"},
        )
        self.assertTrue(resp.is_success)
        self.assertEqual(resp.status, ResponseStatus.SUCCESS)
        self.assertEqual(resp.request_id, "req_1")
        self.assertEqual(resp.session_id, "sess_1")
        self.assertEqual(resp.text, "Registers are fast storage locations inside the CPU.")
        self.assertIsNone(resp.error)
        self.assertEqual(resp.latency_ms, 125.5)

    def test_response_failure_factory(self):
        error = NexusError(
            category="timeout",
            message="Model call timed out",
            code="timeout",
            retryable=True,
            detail="Socket timeout 60s",
        )
        resp = NexusResponse.failure(
            request_id="req_2",
            session_id="sess_2",
            status=ResponseStatus.MODEL_ERROR,
            error=error,
            latency_ms=5000.0,
        )
        self.assertFalse(resp.is_success)
        self.assertEqual(resp.status, ResponseStatus.MODEL_ERROR)
        self.assertEqual(resp.error, error)
        self.assertIsNone(resp.text)

    def test_response_validation_constraints(self):
        # Successful response cannot have an error
        with self.assertRaises(ValueError):
            NexusResponse(
                request_id="req_1",
                response_id="resp_1",
                session_id=None,
                status=ResponseStatus.SUCCESS,
                text="ok",
                error=NexusError(category="err", message="msg", code="c"),
            )

        # Successful response must have text
        with self.assertRaises(ValueError):
            NexusResponse(
                request_id="req_1",
                response_id="resp_1",
                session_id=None,
                status=ResponseStatus.SUCCESS,
                text=None,
            )

        # Failed response must have an error
        with self.assertRaises(ValueError):
            NexusResponse(
                request_id="req_1",
                response_id="resp_1",
                session_id=None,
                status=ResponseStatus.MODEL_ERROR,
                error=None,
            )

    def test_nexus_error_to_dict(self):
        err = NexusError(
            category="provider_unavailable",
            message="Provider down",
            code="provider_unavailable",
            retryable=True,
            detail="Connection reset",
        )
        d = err.to_dict()
        self.assertEqual(d["category"], "provider_unavailable")
        self.assertEqual(d["message"], "Provider down")
        self.assertEqual(d["code"], "provider_unavailable")
        self.assertTrue(d["retryable"])
        self.assertEqual(d["detail"], "Connection reset")


if __name__ == "__main__":
    unittest.main()
