
import unittest
from unittest.mock import patch

from app.memory.memory_store import (
    save_memory,
    get_memory,
    delete_all_user_memories
)
from app.memory.memory_updater import (
    propose_memory_updates,
    review_memory_suggestion,
    approve_memory_suggestion
)
from app.memory.personalized_agent import PersonalizedAgent


class TestPhase3MemoryApproval(unittest.TestCase):

    def setUp(self):
        self.user_id = "phase3_approval_test_user"
        delete_all_user_memories(self.user_id)

    def tearDown(self):
        delete_all_user_memories(self.user_id)

    def test_rejected_suggestion_is_not_saved(self):
        suggestion = {
            "key": "preferred_language",
            "value": "Urdu",
            "category": "preference"
        }

        result = approve_memory_suggestion(
            self.user_id,
            suggestion,
            False
        )

        self.assertFalse(result["saved"])
        self.assertIsNone(
            get_memory(self.user_id, "preferred_language")
        )

    def test_approved_new_memory_is_saved(self):
        suggestion = {
            "key": "preferred_language",
            "value": "English",
            "category": "preference"
        }

        result = approve_memory_suggestion(
            self.user_id,
            suggestion,
            True
        )

        self.assertTrue(result["saved"])

        memory = get_memory(
            self.user_id,
            "preferred_language"
        )

        self.assertEqual(memory["value"], "English")

    def test_conflicting_memory_requires_approval(self):
        save_memory(
            self.user_id,
            "preferred_language",
            "English",
            "preference"
        )

        suggestion = {
            "key": "preferred_language",
            "value": "Urdu",
            "category": "preference"
        }

        conflict = review_memory_suggestion(
            self.user_id,
            suggestion
        )

        self.assertTrue(conflict["conflict"])

        rejected = approve_memory_suggestion(
            self.user_id,
            suggestion,
            False
        )

        self.assertFalse(rejected["saved"])
        self.assertEqual(
            get_memory(self.user_id, "preferred_language")["value"],
            "English"
        )

        approved = approve_memory_suggestion(
            self.user_id,
            suggestion,
            True
        )

        self.assertTrue(approved["saved"])
        self.assertEqual(
            get_memory(self.user_id, "preferred_language")["value"],
            "Urdu"
        )

    def test_duplicate_memory_is_not_saved_twice(self):
        save_memory(
            self.user_id,
            "preferred_language",
            "English",
            "preference"
        )

        suggestion = {
            "key": "preferred_language",
            "value": "English",
            "category": "preference"
        }

        result = approve_memory_suggestion(
            self.user_id,
            suggestion,
            True
        )

        self.assertFalse(result["saved"])

    def test_invalid_approval_value_is_rejected(self):
        suggestion = {
            "key": "preferred_language",
            "value": "English",
            "category": "preference"
        }

        with self.assertRaises(ValueError):
            approve_memory_suggestion(
                self.user_id,
                suggestion,
                "yes"
            )

    def test_agent_does_not_auto_save_suggestions(self):
        suggestion = {
            "key": "preferred_language",
            "value": "Urdu",
            "category": "preference"
        }

        agent = PersonalizedAgent()
        agent.start_chat(self.user_id, "approval_test_chat")

        with patch(
            "app.memory.personalized_agent.generate_response",
            return_value="Hello! How can I help?"
        ), patch(
            "app.memory.personalized_agent.propose_memory_updates",
            return_value=[suggestion]
        ):
            result = agent.chat(
                self.user_id,
                "approval_test_chat",
                "I prefer Urdu."
            )

        self.assertEqual(result["memory_suggestions"], [suggestion])

        self.assertIsNone(
            get_memory(self.user_id, "preferred_language")
        )

        approval = agent.approve_memory(
            self.user_id,
            suggestion,
            True
        )

        self.assertTrue(approval["saved"])

        self.assertEqual(
            get_memory(self.user_id, "preferred_language")["value"],
            "Urdu"
        )


if __name__ == "__main__":
    unittest.main()
