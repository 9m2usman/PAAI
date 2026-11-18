from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
import uuid


class AuditLogger:

    def __init__(self):
        self.records = []
        self.lock = RLock()

    def log(self, user_id, integration, action, status,
            risk_level, approval_status=None, error=None):

        record = {
            "event_id": str(uuid.uuid4()),
            "user_id": user_id,
            "integration": integration,
            "action": action,
            "status": status,
            "risk_level": risk_level,
            "approval_status": approval_status,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        with self.lock:
            self.records.append(record)

        return deepcopy(record)

    def get_user_records(self, user_id):

        with self.lock:
            return [
                deepcopy(record)
                for record in self.records
                if record["user_id"] == user_id
            ]