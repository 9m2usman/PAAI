import hashlib
import json
import uuid
from copy import deepcopy
from threading import RLock


class ApprovalManager:

    def __init__(self):
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

    def request_approval(self, user_id, action_data):

        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid user ID is required.")

        if not isinstance(action_data, dict):
            raise ValueError("Action data must be a dictionary.")

        required_fields = {"integration", "action", "parameters"}

        if not required_fields.issubset(action_data):
            raise ValueError("Incomplete action data.")

        if not isinstance(action_data["integration"], str):
            raise ValueError("Invalid integration.")

        if not isinstance(action_data["action"], str):
            raise ValueError("Invalid action.")

        if not isinstance(action_data["parameters"], dict):
            raise ValueError("Invalid action parameters.")

        approval_id = str(uuid.uuid4())

        fingerprint = self._create_fingerprint(action_data)

        approval = {
            "approval_id": approval_id,
            "user_id": user_id,
            "action_data": deepcopy(action_data),
            "fingerprint": fingerprint,
            "status": "pending"
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

                if (
                    approval["user_id"] == user_id
                    and approval["status"] == "pending"
                ):
                    result.append(deepcopy(approval))

            return result