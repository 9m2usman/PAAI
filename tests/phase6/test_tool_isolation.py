import unittest
from app.auth.token_service import TokenService
from app.identity.context import identity_scope
from app.security.credential_manager import CredentialManager
from app.security.permission_manager import PermissionManager

class ToolIsolationTests(unittest.TestCase):
    def test_user_scoped_credentials_and_permissions(self):
        cm, pm, tokens = CredentialManager(), PermissionManager(), TokenService("t"*40)
        a = tokens.verify_token(tokens.issue_token("a", "a@example.com"))
        b = tokens.verify_token(tokens.issue_token("b", "b@example.com"))
        cm.store_credentials("a", "gmail", {"access_token":"private"})
        pm.grant_permission("a", "gmail", ["read_email"])
        with identity_scope(a):
            self.assertEqual(cm.get_credentials("a", "gmail")["access_token"], "private")
            self.assertTrue(pm.is_allowed("a", "gmail", "read_email"))
        with identity_scope(b):
            self.assertFalse(cm.has_credentials("b", "gmail"))
            self.assertFalse(pm.is_allowed("b", "gmail", "read_email"))
