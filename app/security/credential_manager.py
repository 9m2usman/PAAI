from copy import deepcopy
import threading

class CredentialManager:
    def __init__(self):
        self.credentials = {}
        self._lock = threading.RLock()

    def store_credentials(self, user_id, integration, credentials):
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid user ID is required.")
        if not isinstance(integration, str) or not integration.strip():
            raise ValueError("Integration name is required.")
        if not isinstance(credentials, dict) or not credentials:
            raise ValueError("Valid credentials are required.")
        key = (user_id, integration.strip().lower())
        with self._lock:
            self.credentials[key] = deepcopy(credentials)

    def get_credentials(self, user_id, integration):
        key = (user_id, integration.strip().lower())
        with self._lock:
            if key not in self.credentials:
                raise ValueError("Credentials not found.")
            return deepcopy(self.credentials[key])

    def has_credentials(self, user_id, integration):
        key = (user_id, integration.strip().lower())
        with self._lock:
            return key in self.credentials

    def delete_credentials(self, user_id, integration):
        key = (user_id, integration.strip().lower())
        with self._lock:
            if key not in self.credentials:
                return False
            del self.credentials[key]
            return True
