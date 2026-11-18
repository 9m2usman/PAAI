
import unittest

from app.memory.memory_store import (
    save_memory,
    get_memory,
    delete_all_user_memories
)
from app.memory.memory_controls import (
    review_memories,
    change_memory,
    remove_memory,
    clear_user_memories
)


class TestPhase3MemoryControls(unittest.TestCase):

    def setUp(self):
        self.user_id = "phase3_controls_test_user"
        delete_all_user_memories(self.user_id)

    def tearDown(self):
        delete_all_user_memories(self.user_id)

    def test_review_user_memories(self):
        save_memory(
            self.user_id,
            "preferred_language",
            "English",
            "preference"
        )

        memories = review_memories(self.user_id)

        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["value"], "English")

    def test_update_existing_memory(self):
        save_memory(
            self.user_id,
            "preferred_language",
            "English",
            "preference"
        )

        result = change_memory(
            self.user_id,
            "preferred_language",
            "Urdu"
        )

        self.assertTrue(result)
        self.assertEqual(
            get_memory(self.user_id, "preferred_language")["value"],
            "Urdu"
        )

    def test_delete_specific_memory(self):
        save_memory(
            self.user_id,
            "preferred_language",
            "English",
            "preference"
        )

        result = remove_memory(
            self.user_id,
            "preferred_language"
        )

        self.assertTrue(result)
        self.assertIsNone(
            get_memory(self.user_id, "preferred_language")
        )

    def test_clear_all_user_memories(self):
        save_memory(self.user_id, "language", "English", "preference")
        save_memory(self.user_id, "editor", "VS Code", "preference")

        result = clear_user_memories(self.user_id)

        self.assertTrue(result)
        self.assertEqual(review_memories(self.user_id), [])

    def test_users_cannot_access_each_others_memories(self):
        user_a = self.user_id + "_a"
        user_b = self.user_id + "_b"

        try:
            save_memory(user_a, "language", "English", "preference")
            save_memory(user_b, "language", "Urdu", "preference")

            memories_a = review_memories(user_a)
            memories_b = review_memories(user_b)

            self.assertEqual(memories_a[0]["value"], "English")
            self.assertEqual(memories_b[0]["value"], "Urdu")

            remove_memory(user_a, "language")

            self.assertIsNone(get_memory(user_a, "language"))
            self.assertEqual(
                get_memory(user_b, "language")["value"],
                "Urdu"
            )
        finally:
            delete_all_user_memories(user_a)
            delete_all_user_memories(user_b)


if __name__ == "__main__":
    unittest.main()
