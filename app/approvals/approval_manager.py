import hashlib
import json
import sqlite3
import time
import uuid
from copy import deepcopy
from pathlib import Path
from threading import RLock


class ApprovalManager:
    def __init__(self, approval_ttl_seconds=900, database_path=None):
        if not isinstance(approval_ttl_seconds, (int, float)) or approval_ttl_seconds <= 0:
            raise ValueError("Approval lifetime must be a positive number.")
        self.approval_ttl_seconds = approval_ttl_seconds
        self.database_path = str(database_path) if database_path else ":memory:"
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.db = sqlite3.connect(self.database_path, timeout=20, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS approvals (
            approval_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, action_json TEXT NOT NULL,
            fingerprint TEXT NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL,
            expires_at REAL NOT NULL)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_approvals_owner_status ON approvals(user_id,status)")
        self.db.commit()

    def _fingerprint(self, action_data):
        encoded = json.dumps(action_data, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _row(self, row):
        if row is None:
            return None
        return {
            "approval_id": row["approval_id"], "user_id": row["user_id"],
            "action_data": json.loads(row["action_json"]), "fingerprint": row["fingerprint"],
            "status": row["status"], "created_at": row["created_at"], "expires_at": row["expires_at"],
        }

    def _expire(self, approval_id):
        self.db.execute("""UPDATE approvals SET status='expired'
            WHERE approval_id=? AND status IN ('pending','approved') AND expires_at<=?""",
            (approval_id, time.time()))

    def request_approval(self, user_id, action_data):
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid user ID is required.")
        if not isinstance(action_data, dict) or not {"integration", "action", "parameters"}.issubset(action_data):
            raise ValueError("Incomplete action data.")
        if not isinstance(action_data["integration"], str) or not action_data["integration"].strip():
            raise ValueError("Invalid integration.")
        if not isinstance(action_data["action"], str) or not action_data["action"].strip():
            raise ValueError("Invalid action.")
        if not isinstance(action_data["parameters"], dict):
            raise ValueError("Invalid action parameters.")
        created = time.time()
        safe_data = deepcopy(action_data)
        approval_id = str(uuid.uuid4())
        record = {
            "approval_id": approval_id, "user_id": user_id, "action_data": safe_data,
            "fingerprint": self._fingerprint(safe_data), "status": "pending",
            "created_at": created, "expires_at": created + self.approval_ttl_seconds,
        }
        with self.lock, self.db:
            self.db.execute("""INSERT INTO approvals
                (approval_id,user_id,action_json,fingerprint,status,created_at,expires_at)
                VALUES(?,?,?,?,?,?,?)""",
                (approval_id, user_id, json.dumps(safe_data, sort_keys=True), record["fingerprint"],
                 "pending", created, record["expires_at"]))
        return deepcopy(record)

    def get_approval(self, user_id, approval_id):
        with self.lock, self.db:
            row = self.db.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
            if row is None:
                raise ValueError("Approval request not found.")
            if row["user_id"] != user_id:
                raise PermissionError("Approval belongs to another user.")
            self._expire(approval_id)
            row = self.db.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
            return self._row(row)

    def _decide(self, user_id, approval_id, status):
        with self.lock, self.db:
            row = self.db.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
            if row is None:
                raise ValueError("Approval request not found.")
            if row["user_id"] != user_id:
                raise PermissionError("Approval belongs to another user.")
            self._expire(approval_id)
            row = self.db.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
            if row["status"] != "pending":
                if row["status"] == "expired":
                    raise ValueError("Approval request has expired.")
                raise ValueError("Approval is no longer pending.")
            self.db.execute("UPDATE approvals SET status=? WHERE approval_id=? AND status='pending'",
                            (status, approval_id))
            updated = self.db.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
            return self._row(updated)

    def approve(self, user_id, approval_id):
        return self._decide(user_id, approval_id, "approved")

    def reject(self, user_id, approval_id):
        return self._decide(user_id, approval_id, "rejected")

    def consume_approval(self, user_id, approval_id, action_data):
        with self.lock, self.db:
            row = self.db.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
            if row is None:
                raise ValueError("Approval request not found.")
            if row["user_id"] != user_id:
                raise PermissionError("Approval belongs to another user.")
            self._expire(approval_id)
            row = self.db.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
            if row["status"] == "expired":
                raise PermissionError("Approval request has expired.")
            if row["status"] != "approved":
                raise PermissionError("Action has not been approved.")
            if self._fingerprint(action_data) != row["fingerprint"]:
                raise PermissionError("Action changed after approval.")
            changed = self.db.execute("""UPDATE approvals SET status='consumed'
                WHERE approval_id=? AND user_id=? AND status='approved'""",
                (approval_id, user_id)).rowcount
            if changed != 1:
                raise PermissionError("Approval has already been consumed.")
        return True

    def get_pending_approvals(self, user_id):
        with self.lock, self.db:
            self.db.execute("""UPDATE approvals SET status='expired'
                WHERE user_id=? AND status IN ('pending','approved') AND expires_at<=?""",
                (user_id, time.time()))
            rows = self.db.execute("""SELECT * FROM approvals
                WHERE user_id=? AND status='pending' ORDER BY created_at""", (user_id,)).fetchall()
            return [self._row(row) for row in rows]

    def close(self):
        with self.lock:
            self.db.close()
