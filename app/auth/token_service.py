import base64
import hashlib
import hmac
import json
import os
import time
from dotenv import load_dotenv

def _enc(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

def _dec(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

class TokenService:
    def __init__(self, secret=None, lifetime_seconds=3600):
        load_dotenv()
        self.secret = secret or os.getenv("PAAI_AUTH_SECRET")
        if not self.secret or len(self.secret.encode()) < 32:
            raise ValueError("PAAI_AUTH_SECRET must contain at least 32 characters.")
        if lifetime_seconds < 60:
            raise ValueError("Token lifetime must be at least 60 seconds.")
        self.lifetime_seconds = int(lifetime_seconds)

    def issue_token(self, user_id, email, now=None):
        if not user_id or not email:
            raise ValueError("User identity is required.")
        issued = int(time.time() if now is None else now)
        header = _enc(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(",",":")).encode())
        payload = _enc(json.dumps({"sub":str(user_id),"email":str(email).lower(),"iat":issued,"exp":issued+self.lifetime_seconds}, separators=(",",":")).encode())
        message = (header + "." + payload).encode()
        signature = hmac.new(self.secret.encode(), message, hashlib.sha256).digest()
        return header + "." + payload + "." + _enc(signature)

    def verify_token(self, token, now=None):
        from app.identity.principal import Principal
        try:
            header, payload, signature = token.split(".")
            message = (header + "." + payload).encode()
            expected = hmac.new(self.secret.encode(), message, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _dec(signature)):
                raise PermissionError("Invalid authentication token.")
            head = json.loads(_dec(header))
            data = json.loads(_dec(payload))
            current = int(time.time() if now is None else now)
            if head != {"alg":"HS256","typ":"JWT"} or not isinstance(data.get("exp"), int) or current >= data["exp"]:
                raise PermissionError("Invalid or expired authentication token.")
            if not data.get("sub") or not data.get("email"):
                raise PermissionError("Invalid authentication token.")
            return Principal(data["sub"], data["email"])
        except PermissionError:
            raise
        except Exception:
            raise PermissionError("Invalid authentication token.") from None
