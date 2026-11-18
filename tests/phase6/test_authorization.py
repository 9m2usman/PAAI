import unittest
from app.auth.token_service import TokenService
from app.identity.context import identity_scope
from app.security.permission_manager import PermissionManager
from app.access.authorization_service import AuthorizationService

class AuthorizationTests(unittest.TestCase):
    def test_permission_isolation(self):
        manager, tokens = PermissionManager(), TokenService("p"*40)
        a = tokens.verify_token(tokens.issue_token("a", "a@example.com"))
        b = tokens.verify_token(tokens.issue_token("b", "b@example.com"))
        with identity_scope(a):
            service = AuthorizationService(manager)
            service.grant("gmail", ["read_email"])
            service.require("gmail", "read_email")
        with identity_scope(b):
            with self.assertRaises(PermissionError): AuthorizationService(manager).require("gmail", "read_email")
