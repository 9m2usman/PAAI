import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from app.integrations.google_oauth import GoogleOAuthManager
from app.security.credential_manager import CredentialManager


class GoogleOAuthTests(unittest.TestCase):
    def setUp(self):
        self.credentials = CredentialManager()
        self.manager = GoogleOAuthManager(
            "client-id", "client-secret",
            "http://localhost:8000/auth/google/callback",
            self.credentials,
        )

    def test_authorization_url_contains_oauth_parameters(self):
        url = self.manager.create_authorization_url("user-a")
        self.assertIn("client_id=client-id", url)
        self.assertIn("access_type=offline", url)
        self.assertIn("state=", url)

    @patch.object(GoogleOAuthManager, "_send_token_request")
    def test_callback_binds_credentials_to_state_owner(self, token_request):
        token_request.return_value = {
            "access_token": "access-a", "refresh_token": "refresh-a",
            "expires_in": 3600, "scope": "gmail calendar"
        }
        url = self.manager.create_authorization_url("user-a")
        state = parse_qs(urlparse(url).query)["state"][0]
        result = self.manager.exchange_code_from_state("auth-code", state)
        self.assertEqual(result["status"], "connected")
        self.assertEqual(self.credentials.get_credentials("user-a", "gmail")["access_token"], "access-a")
        self.assertEqual(self.credentials.get_credentials("user-a", "calendar")["access_token"], "access-a")
        with self.assertRaises(ValueError):
            self.credentials.get_credentials("user-b", "gmail")

    def test_state_is_single_use(self):
        url = self.manager.create_authorization_url("user-a")
        state = parse_qs(urlparse(url).query)["state"][0]
        with self.assertRaises(PermissionError):
            self.manager.exchange_code_from_state("code", state)
        with self.assertRaises(PermissionError):
            self.manager.exchange_code_from_state("code", state)
