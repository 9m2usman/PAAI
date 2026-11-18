import hashlib
import json
import time
import uuid
from copy import deepcopy
from threading import RLock


class ApprovalManager:

    def __init__(self, approval_ttl_seconds=900):

        if (
            not isinstance(approval_ttl_seconds, (int, float))
            or approval_ttl_seconds <= 0
        ):
            raise ValueError("Approval lifetime must be a positive number.")

        self.approval_ttl_seconds = approval_ttl_seconds
        self.approvals = {}
        self.lock = RLock()

    def _create_fingerprint(self, action_data):

        action_json = json.dumps(
            action_data,
            sort_keys=True,
            separators=(",", ":"),
            default=str
        )

        return hashlib.sha256(
            action_json.encode("utf-8")
        ).hexdigest()

    def _expire_if_needed(self, approval):

        if (
            approval["status"] in {"pending", "approved"}
            and time.time() >= approval["expires_at"]
        ):
            approval["status"] = "expired"
            return True

        return False

    def request_approval(self, user_id, action_data):

        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid user ID is required.")

        if not isinstance(action_data, dict):
            raise ValueError("Action data must be a dictionary.")

        required_fields = {"integration", "action", "parameters"}

        if not required_fields.issubset(action_data):
            raise ValueError("Incomplete action data.")

        if (
            not isinstance(action_data["integration"], str)
            or not action_data["integration"].strip()
        ):
            raise ValueError("Invalid integration.")

        if (
            not isinstance(action_data["action"], str)
            or not action_data["action"].strip()
        ):
            raise ValueError("Invalid action.")

        if not isinstance(action_data["parameters"], dict):
            raise ValueError("Invalid action parameters.")

        created_at = time.time()
        approval_id = str(uuid.uuid4())
        safe_action_data = deepcopy(action_data)

        approval = {
            "approval_id": approval_id,
            "user_id": user_id,
            "action_data": safe_action_data,
            "fingerprint": self._create_fingerprint(safe_action_data),
            "status": "pending",
            "created_at": created_at,
            "expires_at": created_at + self.approval_ttl_seconds
        }

        with self.lock:
            self.approvals[approval_id] = approval

        return deepcopy(approval)

    def approve(self, user_id, approval_id):

        with self.lock:

            approval = self.approvals.get(approval_id)

            if approval is None:
                raise ValueError("Approval request not found.")

            if approval["user_id"] != user_id:
                raise PermissionError("Approval belongs to another user.")

            if self._expire_if_needed(approval):
                raise ValueError("Approval request has expired.")

            if approval["status"] != "pending":
                raise ValueError("Approval is no longer pending.")

            approval["status"] = "approved"

            return deepcopy(approval)

    def reject(self, user_id, approval_id):

        with self.lock:

            approval = self.approvals.get(approval_id)

            if approval is None:
                raise ValueError("Approval request not found.")

            if approval["user_id"] != user_id:
                raise PermissionError("Approval belongs to another user.")

            if self._expire_if_needed(approval):
                raise ValueError("Approval request has expired.")

            if approval["status"] != "pending":
                raise ValueError("Approval is no longer pending.")

            approval["status"] = "rejected"

            return deepcopy(approval)

    def consume_approval(self, user_id, approval_id, action_data):

        with self.lock:

            approval = self.approvals.get(approval_id)

            if approval is None:
                raise ValueError("Approval request not found.")

            if approval["user_id"] != user_id:
                raise PermissionError("Approval belongs to another user.")

            if self._expire_if_needed(approval):
                raise PermissionError("Approval request has expired.")

            if approval["status"] != "approved":
                raise PermissionError("Action has not been approved.")

            current_fingerprint = self._create_fingerprint(action_data)

            if current_fingerprint != approval["fingerprint"]:
                raise PermissionError("Action changed after approval.")

            approval["status"] = "consumed"

            return True

    def get_pending_approvals(self, user_id):

        with self.lock:

            result = []

            for approval in self.approvals.values():

                self._expire_if_needed(approval)

                if (
                    approval["user_id"] == user_id
                    and approval["status"] == "pending"
                ):
                    result.append(deepcopy(approval))

            return result
