import unittest

from app.conversation.brief import BriefBuilder, ContextBrief
from app.conversation.session import Session, Turn, TurnRole


class ContextBriefTests(unittest.TestCase):
    def test_minimal_brief_creation(self):
        brief = ContextBrief(user_request="What is an algorithm?")
        self.assertEqual(brief.user_request, "What is an algorithm?")
        self.assertEqual(brief.recent_turns, ())
        self.assertEqual(brief.preferences, {})
        self.assertEqual(brief.constraints, ())
        self.assertEqual(brief.evidence, ())

        prompt = brief.render_prompt()
        self.assertIn("Current Request:\nWhat is an algorithm?", prompt)

    def test_validation_rejects_empty_request(self):
        with self.assertRaises(ValueError):
            ContextBrief(user_request="")
        with self.assertRaises(ValueError):
            ContextBrief(user_request="   ")

    def test_full_brief_rendering(self):
        turn1 = Turn(
            turn_id="t1",
            role=TurnRole.USER,
            text="Hello",
        )
        turn2 = Turn(
            turn_id="t2",
            role=TurnRole.ASSISTANT,
            text="Hi, how can I assist you with your studies?",
        )
        brief = ContextBrief(
            user_request="Explain boolean algebra.",
            recent_turns=(turn1, turn2),
            preferences={"tutor_mode": True, "tone": "concise"},
            constraints=("Do not give exam solutions.", "Reference lecture notes."),
            evidence=(
                {"title": "Lecture 2 Notes", "content": "Boolean algebra deals with binary variables."},
            ),
            request_id="req_999",
        )

        prompt = brief.render_prompt()
        self.assertIn("Operational Constraints:", prompt)
        self.assertIn("- Do not give exam solutions.", prompt)
        self.assertIn("- Reference lecture notes.", prompt)
        self.assertIn("Active Preferences:", prompt)
        self.assertIn("- tutor_mode: True", prompt)
        self.assertIn("- tone: concise", prompt)
        self.assertIn("Temporary Reference Evidence:", prompt)
        self.assertIn("[Lecture 2 Notes]:", prompt)
        self.assertIn("Boolean algebra deals with binary variables.", prompt)
        self.assertIn("Recent Conversation:", prompt)
        self.assertIn("User: Hello", prompt)
        self.assertIn("Assistant: Hi, how can I assist you with your studies?", prompt)
        self.assertIn("Current Request:\nExplain boolean algebra.", prompt)

    def test_to_model_request(self):
        brief = ContextBrief(
            user_request="Summarize loop structures.",
            request_id="req_123",
            metadata={"source": "cli"},
        )
        model_req = brief.to_model_request(
            provider="gemini",
            model="gemini-3.8-flash",
            timeout_seconds=30.0,
        )
        self.assertEqual(model_req.provider, "gemini")
        self.assertEqual(model_req.model, "gemini-3.8-flash")
        self.assertEqual(model_req.timeout_seconds, 30.0)
        self.assertIn("Summarize loop structures.", model_req.text or "")
        self.assertEqual(model_req.metadata.get("request_id"), "req_123")
        self.assertEqual(model_req.metadata.get("source"), "cli")

    def test_builder_bounds_context(self):
        session = Session(max_recent_turns=10)
        for i in range(15):
            session.add_user_turn(f"Turn {i}")

        # Build brief bounded to 3 turns
        brief = BriefBuilder.build_brief(
            user_request="Final question",
            session=session,
            max_turns=3,
        )
        self.assertEqual(len(brief.recent_turns), 3)
        self.assertEqual(brief.recent_turns[0].text, "Turn 12")
        self.assertEqual(brief.recent_turns[1].text, "Turn 13")
        self.assertEqual(brief.recent_turns[2].text, "Turn 14")

    def test_ephemeral_nature_no_accidental_persistence(self):
        # Verify that ContextBrief does not write to any store or retain data past its lifetime
        session = Session()
        session.add_user_turn("Initial query")

        brief = BriefBuilder.build_brief(
            user_request="Temporary sub-question",
            session=session,
            evidence=({"source": "temp.txt", "content": "Ephemeral data"},),
        )

        # ContextBrief holds the data
        self.assertEqual(len(brief.evidence), 1)

        # Session remains pristine; it was NOT mutated by building the brief
        self.assertEqual(session.turn_count, 1)
        self.assertEqual(session.turns[0].text, "Initial query")


if __name__ == "__main__":
    unittest.main()
