import re
from app.auth.password_hasher import PasswordHasher
from app.identity.context import IdentityContext

class AuthService:
    def __init__(self, repository, token_service):
        self.repository, self.token_service = repository, token_service
    def register(self, email, password):
        if not isinstance(email, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()):
            raise ValueError("A valid email address is required.")
        user = self.repository.create_user(email, PasswordHasher.hash_password(password))
        return {"user":user, "access_token":self.token_service.issue_token(user["user_id"], user["email"]), "token_type":"Bearer"}
    def login(self, email, password):
        user = self.repository.get_by_email(email) if isinstance(email, str) else None
        if not user or not PasswordHasher.verify_password(password, user["password_hash"]):
            raise PermissionError("Invalid email or password.")
        safe_user = {"user_id":user["user_id"], "email":user["email"]}
        return {"user":safe_user, "access_token":self.token_service.issue_token(user["user_id"], user["email"]), "token_type":"Bearer"}
    def authenticate(self, token):
        principal = self.token_service.verify_token(token)
        user = self.repository.get_by_id(principal.user_id)
        if not user or user["email"] != principal.email:
            raise PermissionError("Authenticated account is unavailable.")
        return IdentityContext(principal)
