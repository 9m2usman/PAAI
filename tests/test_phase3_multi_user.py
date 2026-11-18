
import unittest
from unittest.mock import patch

from app.memory.personalized_agent import PersonalizedAgent
from app.memory.memory_store import save_memory, delete_all_user_memories


class TestMultiUserPersonalization(unittest.TestCase):

    def test_two_users_have_separate_contexts(self):

        user_a = "phase3_test_user_a"
        user_b = "phase3_test_user_b"

        delete_all_user_memories(user_a)
        delete_all_user_memories(user_b)

        try:
            save_memory(
                user_a,
                "preferred_language",
                "English",
                "preference"
            )

            save_memory(
                user_b,
                "preferred_language",
                "Urdu",
                "preference"
            )

            agent = PersonalizedAgent()

            agent.start_chat(user_a, "chat_a")
            agent.start_chat(user_b, "chat_b")

            def fake_response(messages):
                memory_context = messages[1]["content"]
                return memory_context

            with patch(
                "app.memory.personalized_agent.generate_response",
                side_effect=fake_response
            ), patch(
                "app.memory.personalized_agent.propose_memory_updates",
                return_value=[]
            ):

                response_a = agent.chat(
                    user_a,
                    "chat_a",
                    "What language do I prefer?"
                )

                response_b = agent.chat(
                    user_b,
                    "chat_b",
                    "What language do I prefer?"
                )

            self.assertIn("English", response_a["response"])
            self.assertNotIn("Urdu", response_a["response"])

            self.assertIn("Urdu", response_b["response"])
            self.assertNotIn("English", response_b["response"])

            print("PASS: User A received only User A's memory.")
            print("PASS: User B received only User B's memory.")
            print("PASS: Both users used the same agent instance.")

        finally:
            delete_all_user_memories(user_a)
            delete_all_user_memories(user_b)


if __name__ == "__main__":
    unittest.main()
