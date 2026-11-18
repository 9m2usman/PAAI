import threading

class PermissionManager:
    def __init__(self):
        self.permissions = {}
        self.automatic_permissions = {}
        self._lock = threading.RLock()

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
        key = (user_id, integration.strip().lower())
        with self._lock:
            self.permissions.setdefault(key, set()).update(valid)

    def revoke_permission(self, user_id, integration, action):
        key = (user_id, integration.strip().lower())
        with self._lock:
            actions = self.permissions.get(key)
            if not actions or action.strip().lower() not in actions:
                return False
            actions.remove(action.strip().lower())
            automatic = self.automatic_permissions.get(key, set())
            automatic.discard(action.strip().lower())
            return True

    def is_allowed(self, user_id, integration, action):
        key = (user_id, integration.strip().lower())
        with self._lock:
            return action.strip().lower() in self.permissions.get(key, set())

    def list_permissions(self, user_id):
        with self._lock:
            return {
                integration: sorted(actions)
                for (stored_user_id, integration), actions in self.permissions.items()
                if stored_user_id == user_id
            }

    def grant_automatic_permission(self, user_id, integration, action):
        key = (user_id, integration.strip().lower())
        action = action.strip().lower()
        with self._lock:
            if action not in self.permissions.get(key, set()):
                raise PermissionError("Tool permission must be granted first.")
            self.automatic_permissions.setdefault(key, set()).add(action)

    def revoke_automatic_permission(self, user_id, integration, action):
        key = (user_id, integration.strip().lower())
        with self._lock:
            actions = self.automatic_permissions.get(key)
            if not actions or action.strip().lower() not in actions:
                return False
            actions.remove(action.strip().lower())
            return True

    def is_automatic_allowed(self, user_id, integration, action):
        key = (user_id, integration.strip().lower())
        with self._lock:
            return action.strip().lower() in self.automatic_permissions.get(key, set())
