import unittest
from app.auth.token_service import TokenService
from app.identity.context import identity_scope
from app.tenancy.tenant_guard import TenantGuard

class TenantTests(unittest.TestCase):
    def test_tenant_guard(self):
        service = TokenService("z"*40)
        identity = service.verify_token(service.issue_token("a", "a@example.com"))
        with identity_scope(identity):
            self.assertEqual(TenantGuard.require_user("a"), "a")
            with self.assertRaises(PermissionError): TenantGuard.require_user("b")
