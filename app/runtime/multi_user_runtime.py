from app.auth.auth_repository import AuthRepository
from app.auth.auth_service import AuthService
from app.auth.token_service import TokenService
from app.profiles.profile_service import ProfileService
from app.security.credential_manager import CredentialManager
from app.security.permission_manager import PermissionManager
from app.access.authorization_service import AuthorizationService
from app.memory.authenticated_memory import AuthenticatedMemoryService


class MultiUserRuntime:
    def __init__(
        self,
        auth_database="data/paai_auth.db",
        token_secret=None,
        token_lifetime_seconds=3600,
        memory_database=None,
    ):
        self.auth_repository = AuthRepository(auth_database)
        self.token_service = TokenService(token_secret, token_lifetime_seconds)
        self.auth = AuthService(self.auth_repository, self.token_service)
        self.profiles = ProfileService(auth_database)
        self.memory = AuthenticatedMemoryService(
            memory_database if memory_database is not None else None
        )
        self.credentials = CredentialManager()
        self.permissions = PermissionManager()

    def authenticate(self, token):
        return self.auth.authenticate(token)

    def authorization(self):
        return AuthorizationService(self.permissions, self.credentials)
