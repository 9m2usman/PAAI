import time
import json
import secrets
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class GoogleOAuthManager:

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    STATE_TTL_SECONDS = 600

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar"
    ]

    def __init__(
        self,
        client_id,
        client_secret,
        redirect_uri,
        credential_manager
    ):

        if not client_id or not client_secret or not redirect_uri:
            raise ValueError("Google OAuth configuration is incomplete.")

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.credential_manager = credential_manager
        self.pending_states = {}

    def create_authorization_url(self, user_id):

        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid user ID is required.")

        state = secrets.token_urlsafe(32)
        self.pending_states[state] = {
            "user_id": user_id,
            "created_at": time.time()
        }

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state
        }

        return self.AUTH_URL + "?" + urlencode(params)

    def _send_token_request(self, data):

        request = Request(
            self.TOKEN_URL,
            data=urlencode(data).encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            method="POST"
        )

        try:

            with urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))

        except HTTPError as error:
            raise RuntimeError(
                f"Google OAuth request failed: HTTP {error.code}."
            ) from None

        except (URLError, TimeoutError):
            raise RuntimeError(
                "Google OAuth service is unavailable."
            ) from None

    def exchange_code(self, user_id, code, state):

        if not isinstance(code, str) or not code.strip():
            raise ValueError("Authorization code is required.")

        if not isinstance(state, str) or not state:
            raise PermissionError("Invalid or expired OAuth state.")

        state_data = self.pending_states.get(state)

        if not state_data:
            raise PermissionError("Invalid or expired OAuth state.")

        if state_data["user_id"] != user_id:
            raise PermissionError("Invalid or expired OAuth state.")

        if time.time() - state_data["created_at"] > self.STATE_TTL_SECONDS:
            self.pending_states.pop(state, None)
            raise PermissionError("Invalid or expired OAuth state.")

        self.pending_states.pop(state, None)

        token_data = self._send_token_request({
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        })

        if not token_data.get("access_token"):
            raise RuntimeError("Google did not return an access token.")

        credentials = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": time.time() + token_data.get("expires_in", 3600),
            "token_type": token_data.get("token_type", "Bearer"),
            "scope": token_data.get("scope", "")
        }

        self.credential_manager.store_credentials(
            user_id, "gmail", credentials
        )

        self.credential_manager.store_credentials(
            user_id, "calendar", credentials
        )

        return {
            "status": "connected",
            "integrations": ["gmail", "calendar"]
        }

    def get_valid_credentials(self, user_id, integration):

        if integration not in {"gmail", "calendar"}:
            raise ValueError("Unsupported Google integration.")

        credentials = self.credential_manager.get_credentials(
            user_id, integration
        )

        expires_at = credentials.get("expires_at", 0)

        if expires_at > time.time() + 60:
            return credentials

        refresh_token = credentials.get("refresh_token")

        if not refresh_token:
            raise PermissionError(
                "Google authorization expired. Reconnect the account."
            )

        token_data = self._send_token_request({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        })

        if not token_data.get("access_token"):
            raise RuntimeError("Google token refresh failed.")

        credentials["access_token"] = token_data["access_token"]
        credentials["expires_at"] = (
            time.time() + token_data.get("expires_in", 3600)
        )
        credentials["token_type"] = token_data.get(
            "token_type", "Bearer"
        )

        self.credential_manager.store_credentials(
            user_id, integration, credentials
        )

        return credentials

    def exchange_code_from_state(self, code, state):
        if not isinstance(state, str) or not state:
            raise PermissionError("Invalid or expired OAuth state.")
        state_data = self.pending_states.get(state)
        if not state_data:
            raise PermissionError("Invalid or expired OAuth state.")
        user_id = state_data.get("user_id")
        return self.exchange_code(user_id, code, state)

    def create_authorization_url_for_current_identity(self):
        from app.identity.context import current_identity
        return self.create_authorization_url(current_identity().user_id)

    def exchange_code_for_current_identity(self, code, state):
        from app.identity.context import current_identity
        return self.exchange_code(current_identity().user_id, code, state)

    def get_valid_credentials_for_current_identity(self, integration):
        from app.identity.context import current_identity
        return self.get_valid_credentials(current_identity().user_id, integration)
