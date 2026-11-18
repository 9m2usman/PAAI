import unittest
from app.auth.token_service import TokenService
from app.identity.context import current_identity, identity_scope

class IdentityTests(unittest.TestCase):
    def test_context_scope_and_cleanup(self):
        tokens = TokenService("s"*40)
        identity = tokens.verify_token(tokens.issue_token("u1", "a@b.com"))
        with self.assertRaises(PermissionError): current_identity()
        with identity_scope(identity): self.assertEqual(current_identity().user_id, "u1")
        with self.assertRaises(PermissionError): current_identity()
