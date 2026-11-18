import tempfile
import unittest
from pathlib import Path

from app.auth.token_service import TokenService
from app.identity.context import identity_scope
from app.memory.authenticated_memory import AuthenticatedMemoryService
from app.profiles.profile_service import ProfileService


class ProfileIsolationTests(unittest.TestCase):
    def test_profile_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            service = ProfileService(str(Path(folder) / "profiles.db"))
            tokens = TokenService("m" * 40)
            a = tokens.verify_token(tokens.issue_token("a", "a@example.com"))
            b = tokens.verify_token(tokens.issue_token("b", "b@example.com"))

            with identity_scope(a):
                service.update_profile("Alice", {"language": "en"})

            with identity_scope(b):
                self.assertEqual(service.get_profile()["display_name"], "")
                service.update_profile("Bob")

            with identity_scope(a):
                self.assertEqual(service.get_profile()["display_name"], "Alice")


class AuthenticatedMemoryIsolationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        database = str(Path(self.folder.name) / "memory.db")
        self.service = AuthenticatedMemoryService(database)
        tokens = TokenService("n" * 40)
        self.user_a = tokens.verify_token(
            tokens.issue_token("user-a", "a@example.com")
        )
        self.user_b = tokens.verify_token(
            tokens.issue_token("user-b", "b@example.com")
        )

    def tearDown(self):
        self.folder.cleanup()

    def test_memory_and_memory_profile_are_isolated(self):
        with identity_scope(self.user_a):
            self.service.save_memory("language", "English")
            self.service.save_profile({"display_name": "Alice"})

        with identity_scope(self.user_b):
            self.assertIsNone(self.service.get_memory("language"))
            self.assertEqual(self.service.get_memories(), [])
            self.assertEqual(self.service.get_profile(), {})
            self.service.save_memory("language", "Urdu")
            self.service.save_profile({"display_name": "Bob"})

        with identity_scope(self.user_a):
            self.assertEqual(
                self.service.get_memory("language")["value"], "English"
            )
            self.assertEqual(
                self.service.get_profile()["display_name"], "Alice"
            )

        with identity_scope(self.user_b):
            self.assertEqual(
                self.service.get_memory("language")["value"], "Urdu"
            )
            self.assertEqual(
                self.service.get_profile()["display_name"], "Bob"
            )

    def test_service_does_not_accept_a_caller_selected_user_id(self):
        with identity_scope(self.user_a):
            with self.assertRaises(TypeError):
                self.service.get_memory("user-b", "language")

    def test_memory_service_requires_authenticated_identity(self):
        with self.assertRaises(PermissionError):
            self.service.get_memories()
