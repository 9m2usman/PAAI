import tempfile
import unittest
from pathlib import Path

from app.production.crypto import CredentialCipher
from app.security.credential_manager import CredentialManager


class ProductionTests(unittest.TestCase):
    def test_credential_encryption_round_trip(self):
        cipher = CredentialCipher(CredentialCipher.generate_key())
        encrypted = cipher.encrypt("secret-token")
        self.assertNotEqual(encrypted, "secret-token")
        self.assertEqual(cipher.decrypt(encrypted), "secret-token")

    def test_wrong_key_cannot_decrypt(self):
        first = CredentialCipher(CredentialCipher.generate_key())
        second = CredentialCipher(CredentialCipher.generate_key())
        with self.assertRaises(ValueError):
            second.decrypt(first.encrypt("private"))

    def test_credentials_persist_encrypted_and_are_user_isolated(self):
        with tempfile.TemporaryDirectory() as folder:
            database = str(Path(folder) / "credentials.db")
            key = CredentialCipher.generate_key()
            first = CredentialManager(database, key)
            first.store_credentials("user-a", "gmail", {"access_token": "secret-access"})
            restarted = CredentialManager(database, key)
            self.assertEqual(
                restarted.get_credentials("user-a", "gmail")["access_token"],
                "secret-access",
            )
            self.assertFalse(restarted.has_credentials("user-b", "gmail"))
            with self.assertRaises(ValueError):
                restarted.get_credentials("user-b", "gmail")

    def test_credentials_cannot_be_read_with_wrong_encryption_key(self):
        with tempfile.TemporaryDirectory() as folder:
            database = str(Path(folder) / "credentials.db")
            first = CredentialManager(database, CredentialCipher.generate_key())
            first.store_credentials("user-a", "gmail", {"access_token": "secret"})
            second = CredentialManager(database, CredentialCipher.generate_key())
            with self.assertRaises(RuntimeError):
                second.get_credentials("user-a", "gmail")
