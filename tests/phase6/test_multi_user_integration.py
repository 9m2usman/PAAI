import tempfile
import unittest
from pathlib import Path
from app.runtime.multi_user_runtime import MultiUserRuntime
from app.identity.context import identity_scope

class MultiUserIntegrationTests(unittest.TestCase):
    def test_end_to_end_two_users(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = MultiUserRuntime(str(Path(folder)/"auth.db"), "i"*48)
            a = runtime.auth.register("a@example.com", "secure password A")
            b = runtime.auth.register("b@example.com", "secure password B")
            ia, ib = runtime.authenticate(a["access_token"]), runtime.authenticate(b["access_token"])
            with identity_scope(ia): runtime.profiles.update_profile("User A")
            with identity_scope(ib): runtime.profiles.update_profile("User B")
            with identity_scope(ia): self.assertEqual(runtime.profiles.get_profile()["display_name"], "User A")
            with identity_scope(ib): self.assertEqual(runtime.profiles.get_profile()["display_name"], "User B")
