import unittest
from app.auth.auth_repository import AuthRepository
from app.auth.auth_service import AuthService
from app.auth.token_service import TokenService

class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.repo = AuthRepository(":memory:")
        self.tokens = TokenService("x"*48, 120)
        self.auth = AuthService(self.repo, self.tokens)
    def test_register_login(self):
        first = self.auth.register("one@example.com", "correct horse battery")
        second = self.auth.login("ONE@example.com", "correct horse battery")
        self.assertEqual(first["user"]["user_id"], second["user"]["user_id"])
    def test_duplicate_email(self):
        self.auth.register("one@example.com", "correct horse battery")
        with self.assertRaises(ValueError): self.auth.register("ONE@example.com", "another safe password")
    def test_wrong_password(self):
        self.auth.register("one@example.com", "correct horse battery")
        with self.assertRaises(PermissionError): self.auth.login("one@example.com", "wrong password")
    def test_tampered_token(self):
        token = self.auth.register("one@example.com", "correct horse battery")["access_token"]
        altered = token[:-1] + ("a" if token[-1] != "a" else "b")
        with self.assertRaises(PermissionError): self.tokens.verify_token(altered)
    def test_expired_token(self):
        token = self.tokens.issue_token("u1", "one@example.com", now=100)
        with self.assertRaises(PermissionError): self.tokens.verify_token(token, now=220)
