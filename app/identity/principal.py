from dataclasses import dataclass

@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    is_authenticated: bool = True
    def __post_init__(self):
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValueError("A valid authenticated user ID is required.")
        if not isinstance(self.email, str) or not self.email.strip():
            raise ValueError("A valid authenticated user email is required.")
        if self.is_authenticated is not True:
            raise ValueError("Principal must represent an authenticated user.")
