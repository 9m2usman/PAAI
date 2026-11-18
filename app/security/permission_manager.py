class PermissionManager:

    def __init__(self):
        self.permissions = {}

    def grant_permission(self, user_id, integration, actions):

        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid user ID is required.")

        if not isinstance(integration, str) or not integration.strip():
            raise ValueError("Integration name is required.")

        if not isinstance(actions, list) or not actions:
            raise ValueError("At least one action is required.")

        valid_actions = set()

        for action in actions:

            if not isinstance(action, str) or not action.strip():
                raise ValueError("Invalid action.")

            valid_actions.add(action.strip().lower())

        key = (user_id, integration.strip().lower())

        if key not in self.permissions:
            self.permissions[key] = set()

        self.permissions[key].update(valid_actions)

    def revoke_permission(self, user_id, integration, action):

        key = (user_id, integration.strip().lower())

        if key not in self.permissions:
            return False

        action = action.strip().lower()

        if action not in self.permissions[key]:
            return False

        self.permissions[key].remove(action)

        return True

    def is_allowed(self, user_id, integration, action):

        key = (user_id, integration.strip().lower())

        if key not in self.permissions:
            return False

        return action.strip().lower() in self.permissions[key]

    def list_permissions(self, user_id):

        result = {}

        for key, actions in self.permissions.items():

            stored_user_id, integration = key

            if stored_user_id == user_id:
                result[integration] = sorted(actions)

        return result
    
    def grant_automatic_permission(self, user_id, integration, action):

        key = (user_id, integration.strip().lower())
        action = action.strip().lower()

        if not self.is_allowed(user_id, integration, action):
            raise PermissionError(
                "Tool permission must be granted first."
            )

        if not hasattr(self, "automatic_permissions"):
            self.automatic_permissions = {}

        if key not in self.automatic_permissions:
            self.automatic_permissions[key] = set()

        self.automatic_permissions[key].add(action)

    def revoke_automatic_permission(self, user_id, integration, action):

        key = (user_id, integration.strip().lower())

        if not hasattr(self, "automatic_permissions"):
            return False

        if key not in self.automatic_permissions:
            return False

        action = action.strip().lower()

        if action not in self.automatic_permissions[key]:
            return False

        self.automatic_permissions[key].remove(action)

        return True

    def is_automatic_allowed(self, user_id, integration, action):

        key = (user_id, integration.strip().lower())

        if not hasattr(self, "automatic_permissions"):
            return False

        if key not in self.automatic_permissions:
            return False

        return action.strip().lower() in self.automatic_permissions[key]