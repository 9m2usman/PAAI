import sqlite3
import threading
from pathlib import Path


class PermissionManager:
    def __init__(self, database_path=None):
        self.database_path = str(database_path) if database_path else ":memory:"
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.db = sqlite3.connect(self.database_path, timeout=20, check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS integration_permissions (
            user_id TEXT NOT NULL, integration TEXT NOT NULL, action TEXT NOT NULL,
            automatic INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id,integration,action))""")
        self.db.commit()

    def grant_permission(self, user_id, integration, actions):
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid user ID is required.")
        if not isinstance(integration, str) or not integration.strip():
            raise ValueError("Integration name is required.")
        if not isinstance(actions, list) or not actions:
            raise ValueError("At least one action is required.")
        valid = set()
        for action in actions:
            if not isinstance(action, str) or not action.strip():
                raise ValueError("Invalid action.")
            valid.add(action.strip().lower())
        with self._lock, self.db:
            for action in valid:
                self.db.execute("""INSERT OR IGNORE INTO integration_permissions
                    (user_id,integration,action,automatic) VALUES(?,?,?,0)""",
                    (user_id, integration.strip().lower(), action))

    def revoke_permission(self, user_id, integration, action):
        with self._lock, self.db:
            cursor = self.db.execute("""DELETE FROM integration_permissions
                WHERE user_id=? AND integration=? AND action=?""",
                (user_id, integration.strip().lower(), action.strip().lower()))
            return cursor.rowcount > 0

    def is_allowed(self, user_id, integration, action):
        with self._lock:
            row = self.db.execute("""SELECT 1 FROM integration_permissions
                WHERE user_id=? AND integration=? AND action=?""",
                (user_id, integration.strip().lower(), action.strip().lower())).fetchone()
            return row is not None

    def list_permissions(self, user_id):
        with self._lock:
            rows = self.db.execute("""SELECT integration,action FROM integration_permissions
                WHERE user_id=? ORDER BY integration,action""", (user_id,)).fetchall()
        result = {}
        for integration, action in rows:
            result.setdefault(integration, []).append(action)
        return result

    def grant_automatic_permission(self, user_id, integration, action):
        with self._lock, self.db:
            cursor = self.db.execute("""UPDATE integration_permissions SET automatic=1
                WHERE user_id=? AND integration=? AND action=?""",
                (user_id, integration.strip().lower(), action.strip().lower()))
            if cursor.rowcount != 1:
                raise PermissionError("Tool permission must be granted first.")

    def revoke_automatic_permission(self, user_id, integration, action):
        with self._lock, self.db:
            cursor = self.db.execute("""UPDATE integration_permissions SET automatic=0
                WHERE user_id=? AND integration=? AND action=? AND automatic=1""",
                (user_id, integration.strip().lower(), action.strip().lower()))
            return cursor.rowcount > 0

    def is_automatic_allowed(self, user_id, integration, action):
        with self._lock:
            row = self.db.execute("""SELECT 1 FROM integration_permissions
                WHERE user_id=? AND integration=? AND action=? AND automatic=1""",
                (user_id, integration.strip().lower(), action.strip().lower())).fetchone()
            return row is not None

    def close(self):
        with self._lock:
            self.db.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
