from contextvars import ContextVar
from dataclasses import dataclass
from app.identity.principal import Principal

_identity = ContextVar("paai_identity", default=None)

@dataclass(frozen=True)
class IdentityContext:
    principal: Principal

    def __post_init__(self):
        if not isinstance(self.principal, Principal):
            raise TypeError("IdentityContext requires a Principal.")

    @property
    def user_id(self):
        return self.principal.user_id

    @property
    def email(self):
        return self.principal.email

def current_identity(required=True):
    value = _identity.get()
    if value is None and required:
        raise PermissionError("An authenticated identity context is required.")
    return value

class identity_scope:
    def __init__(self, identity):
        if isinstance(identity, Principal):
            identity = IdentityContext(identity)
        if not isinstance(identity, IdentityContext):
            raise TypeError("A verified Principal or IdentityContext is required.")
        self.identity = identity
        self.token = None

    def __enter__(self):
        self.token = _identity.set(self.identity)
        return self.identity

    def __exit__(self, exc_type, exc_value, traceback):
        _identity.reset(self.token)
        return False
