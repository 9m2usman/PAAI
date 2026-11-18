import json
import sqlite3
from contextlib import contextmanager
import threading
from pathlib import Path
from app.identity.context import current_identity

class ProfileService:
    def __init__(self, database_path="data/paai_auth.db"):
        self.database_path = str(database_path)
        self.lock = threading.RLock()
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self.lock, self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS authenticated_user_profiles (
                user_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL DEFAULT '',
                preferences TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database_path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get_profile(self):
        uid = current_identity().user_id
        with self.lock, self.connect() as db:
            row = db.execute(
                "SELECT * FROM authenticated_user_profiles WHERE user_id=?", (uid,)
            ).fetchone()
        if not row:
            return {"user_id": uid, "display_name": "", "preferences": {}}
        result = dict(row)
        result["preferences"] = json.loads(result["preferences"])
        return result

    def update_profile(self, display_name=None, preferences=None):
        uid = current_identity().user_id
        if display_name is not None and not isinstance(display_name, str):
            raise ValueError("Display name must be text.")
        if preferences is not None and not isinstance(preferences, dict):
            raise ValueError("Preferences must be an object.")
        current = self.get_profile()
        name = current["display_name"] if display_name is None else display_name.strip()
        prefs = current["preferences"] if preferences is None else preferences
        with self.lock, self.connect() as db:
            db.execute("""INSERT INTO authenticated_user_profiles
                (user_id,display_name,preferences) VALUES(?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET
                display_name=excluded.display_name,
                preferences=excluded.preferences,
                updated_at=CURRENT_TIMESTAMP""",
                (uid, name, json.dumps(prefs, ensure_ascii=False)))
        return self.get_profile()
