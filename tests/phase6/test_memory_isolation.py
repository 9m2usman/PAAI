import tempfile
import unittest
from pathlib import Path
from app.auth.token_service import TokenService
from app.identity.context import identity_scope
from app.profiles.profile_service import ProfileService

class ProfileIsolationTests(unittest.TestCase):
    def test_profile_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            service = ProfileService(str(Path(folder)/"profiles.db"))
            tokens = TokenService("m"*40)
            a = tokens.verify_token(tokens.issue_token("a", "a@example.com"))
            b = tokens.verify_token(tokens.issue_token("b", "b@example.com"))
            with identity_scope(a): service.update_profile("Alice", {"language":"en"})
            with identity_scope(b):
                self.assertEqual(service.get_profile()["display_name"], "")
                service.update_profile("Bob")
            with identity_scope(a): self.assertEqual(service.get_profile()["display_name"], "Alice")
