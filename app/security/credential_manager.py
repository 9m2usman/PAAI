import json
import sqlite3
import threading
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

from app.production.crypto import CredentialCipher


class CredentialManager:
    def __init__(self, database_path=None, encryption_key=None):
        self.database_path = str(database_path) if database_path else None
        self.credentials = {}
        self._lock = threading.RLock()
        self._cipher = CredentialCipher(encryption_key) if encryption_key else None

        if self.database_path and self._cipher is None:
            raise ValueError("Credential encryption key is required for persistent credential storage.")

        if self.database_path:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
            with self._connection() as connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS integration_credentials (
                        user_id TEXT NOT NULL,
                        integration TEXT NOT NULL,
                        encrypted_payload TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, integration)
                    )
                """)

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.database_path, timeout=15)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def store_credentials(self, user_id, integration, credentials):
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid user ID is required.")
        if not isinstance(integration, str) or not integration.strip():
            raise ValueError("Integration name is required.")
        if not isinstance(credentials, dict) or not credentials:
            raise ValueError("Valid credentials are required.")

        key = (user_id, integration.strip().lower())
        copied = deepcopy(credentials)
        with self._lock:
            if self.database_path:
                encrypted = self._cipher.encrypt(json.dumps(copied, separators=(",", ":")))
                with self._connection() as connection:
                    connection.execute("""
                        INSERT INTO integration_credentials(user_id, integration, encrypted_payload)
                        VALUES (?, ?, ?)
                        ON CONFLICT(user_id, integration) DO UPDATE SET
                            encrypted_payload=excluded.encrypted_payload,
                            updated_at=CURRENT_TIMESTAMP
                    """, (key[0], key[1], encrypted))
            else:
                self.credentials[key] = copied

    def get_credentials(self, user_id, integration):
        key = (user_id, integration.strip().lower())
        with self._lock:
            if self.database_path:
                with self._connection() as connection:
                    row = connection.execute(
                        "SELECT encrypted_payload FROM integration_credentials WHERE user_id=? AND integration=?",
                        key
                    ).fetchone()
                if row is None:
                    raise ValueError("Credentials not found.")
                try:
                    return json.loads(self._cipher.decrypt(row[0]))
                except (ValueError, json.JSONDecodeError):
                    raise RuntimeError("Stored integration credentials could not be decrypted.") from None

            if key not in self.credentials:
                raise ValueError("Credentials not found.")
            return deepcopy(self.credentials[key])

    def has_credentials(self, user_id, integration):
        try:
            self.get_credentials(user_id, integration)
            return True
        except ValueError:
            return False

    def delete_credentials(self, user_id, integration):
        key = (user_id, integration.strip().lower())
        with self._lock:
            if self.database_path:
                with self._connection() as connection:
                    cursor = connection.execute(
                        "DELETE FROM integration_credentials WHERE user_id=? AND integration=?",
                        key
                    )
                    return cursor.rowcount > 0
            return self.credentials.pop(key, None) is not None
