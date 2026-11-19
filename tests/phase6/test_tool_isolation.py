import unittest
from app.auth.token_service import TokenService
from app.identity.context import identity_scope
from app.security.credential_manager import CredentialManager
from app.security.permission_manager import PermissionManager
from app.access.authorization_service import AuthorizationService

class ToolIsolationTests(unittest.TestCase):
    def test_credentials_and_permissions_are_user_scoped(self):
        cm, pm, tokens = CredentialManager(), PermissionManager(), TokenService("t"*40)
        a = tokens.verify_token(tokens.issue_token("a", "a@example.com"))
        b = tokens.verify_token(tokens.issue_token("b", "b@example.com"))
        access_a = AuthorizationService(pm, cm)
        access_b = AuthorizationService(pm, cm)
        with identity_scope(a):
            access_a.store_credentials("gmail", {"access_token":"private"})
            access_a.grant("gmail", ["read_email"])
            self.assertEqual(access_a.get_credentials("gmail")["access_token"], "private")
            access_a.require("gmail", "read_email")
        with identity_scope(b):
            with self.assertRaises(ValueError):
                access_b.get_credentials("gmail")
            with self.assertRaises(PermissionError):
                access_b.require("gmail", "read_email")
