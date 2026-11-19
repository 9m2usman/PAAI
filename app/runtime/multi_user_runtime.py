from app.auth.auth_repository import AuthRepository
from app.auth.auth_service import AuthService
from app.auth.token_service import TokenService
from app.profiles.profile_service import ProfileService
from app.security.credential_manager import CredentialManager
from app.security.permission_manager import PermissionManager
from app.access.authorization_service import AuthorizationService
from app.memory.authenticated_memory import AuthenticatedMemoryService
from app.autonomy.goal_repository import GoalRepository
from app.autonomy.goal_service import GoalService
from app.autonomy.policy import AutonomyPolicy
from app.autonomy.triggers import TriggerRegistry
from app.autonomy.engine import AutonomyEngine
from app.autonomy.scheduler import AutonomyScheduler
from app.autonomy.agent_executor import ReasoningGoalExecutor
from app.integrations.google_oauth import GoogleOAuthManager


class MultiUserRuntime:
    def __init__(
        self,
        auth_database="data/paai_auth.db",
        token_secret=None,
        token_lifetime_seconds=3600,
        memory_database=None,
        autonomy_database="data/paai_autonomy.db",
        autonomy_executor=None,
        google_oauth_config=None,
        credential_database=None,
        credential_encryption_key=None,
    ):
        self.auth_repository = AuthRepository(auth_database)
        self.token_service = TokenService(token_secret, token_lifetime_seconds)
        self.auth = AuthService(self.auth_repository, self.token_service)
        self.profiles = ProfileService(auth_database)
        self.memory = AuthenticatedMemoryService(
            memory_database if memory_database is not None else None
        )
        self.credentials = CredentialManager(
            database_path=credential_database,
            encryption_key=credential_encryption_key,
        )
        self.google_oauth = None
        if google_oauth_config:
            self.google_oauth = GoogleOAuthManager(
                client_id=google_oauth_config["client_id"],
                client_secret=google_oauth_config["client_secret"],
                redirect_uri=google_oauth_config["redirect_uri"],
                credential_manager=self.credentials,
            )
        self.permissions = PermissionManager()
        self.autonomy_policy = AutonomyPolicy()
        self.goal_repository = GoalRepository(autonomy_database)
        self.goals = GoalService(self.goal_repository, self.autonomy_policy)
        self.triggers = TriggerRegistry(
            max_payload_bytes=self.autonomy_policy.max_event_payload_bytes
        )
        self.autonomy_engine = AutonomyEngine(
            self.goal_repository,
            autonomy_executor or ReasoningGoalExecutor(),
            self.autonomy_policy,
        )
        self.scheduler = AutonomyScheduler(self.autonomy_engine)

    def authenticate(self, token):
        return self.auth.authenticate(token)

    def authorization(self):
        return AuthorizationService(self.permissions, self.credentials)
