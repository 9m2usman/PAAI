
import unittest

from app.memory.memory_store import (
    save_memory,
    get_memory,
    update_memory,
    delete_all_user_memories
)
from app.memory.memory_conflicts import (
    detect_memory_conflict,
    resolve_memory_conflict
)


class TestPhase3MemoryConflicts(unittest.TestCase):

    def setUp(self):
        self.user_id = "phase3_conflict_test_user"
        delete_all_user_memories(self.user_id)

    def tearDown(self):
        delete_all_user_memories(self.user_id)

    def test_detect_different_values(self):
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

        conflict = detect_memory_conflict(
            self.user_id,
            suggestion
        )

        self.assertTrue(conflict["conflict"])

    def test_same_value_is_not_a_conflict(self):
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

        conflict = detect_memory_conflict(
            self.user_id,
            suggestion
        )

        self.assertFalse(conflict["conflict"])

    def test_rejected_conflict_preserves_existing_memory(self):
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

        conflict = detect_memory_conflict(
            self.user_id,
            suggestion
        )

        result = resolve_memory_conflict(
            self.user_id,
            conflict,
            False
        )

        self.assertFalse(result["updated"])
        self.assertEqual(
            get_memory(self.user_id, "preferred_language")["value"],
            "English"
        )

    def test_stale_conflict_does_not_overwrite_newer_memory(self):
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

        conflict = detect_memory_conflict(
            self.user_id,
            suggestion
        )

        update_memory(
            self.user_id,
            "preferred_language",
            "Chinese",
            "preference"
        )

        result = resolve_memory_conflict(
            self.user_id,
            conflict,
            True
        )

        self.assertFalse(result["updated"])
        self.assertEqual(
            get_memory(self.user_id, "preferred_language")["value"],
            "Chinese"
        )

    def test_invalid_conflict_data_is_rejected(self):
        with self.assertRaises(ValueError):
            detect_memory_conflict(
                self.user_id,
                {"key": "language"}
            )

    def test_invalid_approval_value_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_memory_conflict(
                self.user_id,
                {"conflict": True},
                "yes"
            )


if __name__ == "__main__":
    unittest.main()
