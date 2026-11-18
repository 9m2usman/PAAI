import unittest
from app.production.crypto import CredentialCipher

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
