import concurrent.futures
import unittest
from app.auth.token_service import TokenService
from app.identity.context import identity_scope, current_identity

class ConcurrencyTests(unittest.TestCase):
    def test_thread_identity_isolation(self):
        tokens = TokenService("c"*40)
        identities = [
            tokens.verify_token(tokens.issue_token("a","a@x.com")),
            tokens.verify_token(tokens.issue_token("b","b@x.com"))
        ]
        def read(identity):
            with identity_scope(identity): return current_identity().user_id
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertEqual(list(pool.map(read, identities)), ["a","b"])
