from cryptography.fernet import Fernet, InvalidToken

class CredentialCipher:
    def __init__(self, key):
        if not isinstance(key, (str, bytes)) or not key:
            raise ValueError("A Fernet encryption key is required.")
        self.fernet = Fernet(key.encode() if isinstance(key, str) else key)

    @staticmethod
    def generate_key():
        return Fernet.generate_key().decode("ascii")

    def encrypt(self, value):
        if not isinstance(value, str):
            raise TypeError("Credential value must be text.")
        return self.fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, token):
        try:
            return self.fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeError, ValueError):
            raise ValueError("Credential could not be decrypted with this key.") from None
