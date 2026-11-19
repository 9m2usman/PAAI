import tempfile
import unittest
from pathlib import Path

from app.runtime.multi_user_runtime import MultiUserRuntime
from app.identity.context import identity_scope


class MultiUserIntegrationTests(unittest.TestCase):
    def test_end_to_end_two_users(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = MultiUserRuntime(
                str(Path(folder) / "auth.db"),
                "i" * 48,
                memory_database=str(Path(folder) / "memory.db"),
            )
            a = runtime.auth.register("a@example.com", "secure password A")
            b = runtime.auth.register("b@example.com", "secure password B")
            ia = runtime.authenticate(a["access_token"])
            ib = runtime.authenticate(b["access_token"])

            with identity_scope(ia):
                runtime.profiles.update_profile("User A")
                runtime.memory.save_memory("language", "English")

            with identity_scope(ib):
                runtime.profiles.update_profile("User B")
                runtime.memory.save_memory("language", "Urdu")

            with identity_scope(ia):
                self.assertEqual(
                    runtime.profiles.get_profile()["display_name"], "User A"
                )
                self.assertEqual(
                    runtime.memory.get_memory("language")["value"], "English"
                )

            with identity_scope(ib):
                self.assertEqual(
                    runtime.profiles.get_profile()["display_name"], "User B"
                )
                self.assertEqual(
                    runtime.memory.get_memory("language")["value"], "Urdu"
                )
