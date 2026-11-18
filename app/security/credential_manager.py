from copy import deepcopy


class CredentialManager:

    def __init__(self):
        self.credentials = {}

    def store_credentials(self, user_id, integration, credentials):

        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid user ID is required.")

        if not isinstance(integration, str) or not integration.strip():
            raise ValueError("Integration name is required.")

        if not isinstance(credentials, dict) or not credentials:
            raise ValueError("Valid credentials are required.")

        key = (user_id, integration.strip().lower())

        self.credentials[key] = deepcopy(credentials)

    def get_credentials(self, user_id, integration):

        key = (user_id, integration.strip().lower())

        if key not in self.credentials:
            raise ValueError("Credentials not found.")

        return deepcopy(self.credentials[key])

    def has_credentials(self, user_id, integration):

        key = (user_id, integration.strip().lower())

        return key in self.credentials

    def delete_credentials(self, user_id, integration):

        key = (user_id, integration.strip().lower())

        if key not in self.credentials:
            return False

        del self.credentials[key]

        return True