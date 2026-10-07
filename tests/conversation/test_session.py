import unittest

from app.conversation.session import Session, SessionStore, Turn, TurnRole


class SessionCoreTests(unittest.TestCase):
    def test_session_creation_with_generated_id(self):
        session = Session()
        self.assertTrue(isinstance(session.session_id, str))
        self.assertGreater(len(session.session_id), 0)
        self.assertEqual(session.turn_count, 0)
        self.assertTrue(isinstance(session.created_at, str))
        self.assertEqual(session.created_at, session.updated_at)

    def test_session_creation_with_explicit_id(self):
        session = Session(session_id="custom-session-42", max_recent_turns=5)
        self.assertEqual(session.session_id, "custom-session-42")
        self.assertEqual(session.max_recent_turns, 5)

    def test_session_invalid_initialization(self):
        with self.assertRaises(ValueError):
            Session(session_id="   ")
        with self.assertRaises(ValueError):
            Session(max_recent_turns=0)
        with self.assertRaises(ValueError):
            Session(max_recent_turns=-1)

    def test_turn_creation_and_validation(self):
        turn = Turn(
            turn_id="turn_1",
            role=TurnRole.USER,
            text="Hello Nexus",
            request_id="req_100",
        )
        self.assertEqual(turn.turn_id, "turn_1")
        self.assertEqual(turn.role, TurnRole.USER)
        self.assertEqual(turn.text, "Hello Nexus")
        self.assertEqual(turn.request_id, "req_100")
        self.assertIsNone(turn.response_id)
        self.assertIn("timestamp", turn.to_dict())

        with self.assertRaises(ValueError):
            Turn(turn_id="", role=TurnRole.USER, text="Hi")

        with self.assertRaises(ValueError):
            Turn(turn_id="turn_2", role="user", text="Hi")  # type: ignore

        with self.assertRaises(ValueError):
            Turn(turn_id="turn_3", role=TurnRole.USER, text="")

    def test_ordered_turns_and_timestamps(self):
        session = Session()
        t1 = session.add_user_turn("Question 1", request_id="req_1")
        t2 = session.add_assistant_turn("Answer 1", request_id="req_1", response_id="resp_1")
        t3 = session.add_system_turn("System note: context updated")
        t4 = session.add_user_turn("Question 2", request_id="req_2")

        self.assertEqual(session.turn_count, 4)
        turns = session.turns
        self.assertEqual(turns[0], t1)
        self.assertEqual(turns[1], t2)
        self.assertEqual(turns[2], t3)
        self.assertEqual(turns[3], t4)

        self.assertEqual(t1.role, TurnRole.USER)
        self.assertEqual(t2.role, TurnRole.ASSISTANT)
        self.assertEqual(t3.role, TurnRole.SYSTEM)
        self.assertEqual(t4.role, TurnRole.USER)

        self.assertTrue(t1.timestamp <= t2.timestamp <= t3.timestamp <= t4.timestamp)

    def test_bounded_recent_context(self):
        session = Session(max_recent_turns=3)
        for i in range(10):
            session.add_user_turn(f"Message {i}")

        self.assertEqual(session.turn_count, 10)
        recent_default = session.get_recent_turns()
        self.assertEqual(len(recent_default), 3)
        self.assertEqual(recent_default[0].text, "Message 7")
        self.assertEqual(recent_default[1].text, "Message 8")
        self.assertEqual(recent_default[2].text, "Message 9")

        # Explicit limit
        recent_custom = session.get_recent_turns(limit=2)
        self.assertEqual(len(recent_custom), 2)
        self.assertEqual(recent_custom[0].text, "Message 8")
        self.assertEqual(recent_custom[1].text, "Message 9")

    def test_session_reset(self):
        session = Session(session_id="test-session")
        session.add_user_turn("Hello")
        session.add_assistant_turn("Hi")
        self.assertEqual(session.turn_count, 2)

        session.reset()
        self.assertEqual(session.turn_count, 0)
        self.assertEqual(session.turns, ())
        self.assertEqual(session.session_id, "test-session")

    def test_session_to_dict(self):
        session = Session(session_id="sess_abc")
        session.add_user_turn("Test msg")
        d = session.to_dict()
        self.assertEqual(d["session_id"], "sess_abc")
        self.assertEqual(d["turn_count"], 1)
        self.assertEqual(len(d["turns"]), 1)
        self.assertEqual(d["turns"][0]["text"], "Test msg")


class SessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = SessionStore()

    def test_create_and_get_session(self):
        session = self.store.create_session("sess-1")
        self.assertEqual(session.session_id, "sess-1")
        fetched = self.store.get_session("sess-1")
        self.assertIs(fetched, session)

    def test_duplicate_session_id_rejected(self):
        self.store.create_session("sess-dup")
        with self.assertRaises(ValueError):
            self.store.create_session("sess-dup")

    def test_get_or_create_session(self):
        s1 = self.store.get_or_create_session("sess-auto")
        s2 = self.store.get_or_create_session("sess-auto")
        self.assertIs(s1, s2)

    def test_reset_session(self):
        s = self.store.create_session("sess-to-reset")
        s.add_user_turn("hello")
        self.assertEqual(s.turn_count, 1)

        reset_result = self.store.reset_session("sess-to-reset")
        self.assertIsNotNone(reset_result)
        self.assertEqual(reset_result.turn_count, 0)

        # Reset non-existent
        self.assertIsNone(self.store.reset_session("nonexistent"))

    def test_delete_and_list_sessions(self):
        self.store.create_session("s1")
        self.store.create_session("s2")
        self.assertEqual(set(self.store.list_sessions()), {"s1", "s2"})

        self.assertTrue(self.store.delete_session("s1"))
        self.assertFalse(self.store.delete_session("s1"))
        self.assertEqual(self.store.list_sessions(), ("s2",))

    def test_clear_all(self):
        self.store.create_session("s1")
        self.store.create_session("s2")
        self.store.clear_all()
        self.assertEqual(self.store.list_sessions(), ())


if __name__ == "__main__":
    unittest.main()
