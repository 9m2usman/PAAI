import hashlib
import hmac
import secrets

class PasswordHasher:
    ITERATIONS = 310000

    @classmethod
    def hash_password(cls, password):
        if not isinstance(password, str) or len(password) < 10:
            raise ValueError("Password must contain at least 10 characters.")
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, cls.ITERATIONS)
        return "pbkdf2_sha256$%s$%s$%s" % (cls.ITERATIONS, salt.hex(), digest.hex())

    @staticmethod
    def verify_password(password, encoded):
        try:
            algorithm, rounds, salt, digest = encoded.split("$")
            if algorithm != "pbkdf2_sha256":
                return False
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
            return hmac.compare_digest(actual, bytes.fromhex(digest))
        except (AttributeError, TypeError, ValueError):
            return False
