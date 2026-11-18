import sqlite3
from contextlib import contextmanager
import threading
import uuid
from pathlib import Path

class AuthRepository:
    def __init__(self, database_path="data/paai_auth.db"):
        self.database_path = str(database_path)
        self.lock = threading.RLock()
        self.uri = self.database_path == ":memory:"
        self._keeper = None
        if self.uri:
            self.database_path = "file:paai_auth_%s?mode=memory&cache=shared" % uuid.uuid4().hex
            self._keeper = sqlite3.connect(
                self.database_path, uri=True, check_same_thread=False
            )
        else:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self.lock, self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS auth_users (
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database_path, timeout=15, uri=self.uri)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def create_user(self, email, password_hash):
        user = {"user_id": str(uuid.uuid4()), "email": email.strip().lower()}
        try:
            with self.lock, self.connect() as db:
                db.execute(
                    "INSERT INTO auth_users(user_id,email,password_hash) VALUES(?,?,?)",
                    (user["user_id"], user["email"], password_hash)
                )
        except sqlite3.IntegrityError:
            raise ValueError("An account with this email already exists.") from None
        return user

    def get_by_email(self, email):
        with self.lock, self.connect() as db:
            row = db.execute(
                "SELECT * FROM auth_users WHERE email=? COLLATE NOCASE",
                (email.strip().lower(),)
            ).fetchone()
        return dict(row) if row else None

    def get_by_id(self, user_id):
        with self.lock, self.connect() as db:
            row = db.execute(
                "SELECT user_id,email FROM auth_users WHERE user_id=?", (user_id,)
            ).fetchone()
        return dict(row) if row else None

    def close(self):
        if self._keeper is not None:
            self._keeper.close()
            self._keeper = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
