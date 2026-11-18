
import unittest
from unittest.mock import patch

from app.memory.personalized_agent import PersonalizedAgent
from app.memory.memory_store import (
    get_memory,
    delete_all_user_memories
)


class TestPhase3EndToEnd(unittest.TestCase):

    def setUp(self):
        self.user_id = "phase3_e2e_test_user"
        self.conversation_id = "phase3_e2e_chat"
        delete_all_user_memories(self.user_id)

    def tearDown(self):
        delete_all_user_memories(self.user_id)

    def test_complete_memory_lifecycle(self):
        suggestion = {
            "key": "preferred_language",
            "value": "Urdu",
            "category": "preference"
        }

        agent = PersonalizedAgent()
        agent.start_chat(self.user_id, self.conversation_id)

        def fake_response(messages):
            return messages[1]["content"]

        with patch(
            "app.memory.personalized_agent.generate_response",
            side_effect=fake_response
        ), patch(
            "app.memory.personalized_agent.propose_memory_updates",
            return_value=[suggestion]
        ):

            first_result = agent.chat(
                self.user_id,
                self.conversation_id,
                "I prefer Urdu."
            )

            self.assertEqual(
                first_result["memory_suggestions"],
                [suggestion]
            )

            self.assertIsNone(
                get_memory(self.user_id, "preferred_language")
            )

            approval = agent.approve_memory(
                self.user_id,
                suggestion,
                True
            )

            self.assertTrue(approval["saved"])

            second_result = agent.chat(
                self.user_id,
                self.conversation_id,
                "What language do I prefer?"
            )

            self.assertIn(
                "Urdu",
                second_result["response"]
            )

        print("PASS: Agent proposed a memory.")
        print("PASS: Memory was not saved automatically.")
        print("PASS: User approval saved the memory.")
        print("PASS: Agent retrieved the approved memory.")
        print("PASS: Complete memory lifecycle succeeded.")


if __name__ == "__main__":
    unittest.main()

