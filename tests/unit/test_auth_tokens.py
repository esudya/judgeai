import unittest

from src.services.auth_tokens import csrf_for, new_session_token, token_digest


class SessionTokenTests(unittest.TestCase):
    def test_independent_random_tokens_and_digests(self):
        tokens = {new_session_token() for _ in range(100)}
        self.assertEqual(len(tokens), 100)
        for token in tokens:
            self.assertGreaterEqual(len(token), 43)
            self.assertEqual(len(token_digest(token)), 64)
            self.assertNotEqual(token_digest(token), token)

    def test_csrf_is_bound_to_session_and_domain_separated(self):
        first, second = new_session_token(), new_session_token()
        self.assertNotEqual(csrf_for(first), csrf_for(second))
        self.assertNotEqual(csrf_for(first), token_digest(first))
        self.assertEqual(csrf_for(first), csrf_for(first))


class LoginBucketTests(unittest.TestCase):
    def test_account_limits_are_independent_behind_shared_proxy(self):
        from src.services.auth_tokens import login_bucket_keys

        alice, host = login_bucket_keys("proxy", "Alice")
        bob, same_host = login_bucket_keys("proxy", "bob")
        self.assertNotEqual(alice, bob)
        self.assertEqual(host, same_host)
        self.assertEqual(login_bucket_keys("other-ip", "alice")[0], alice)
        self.assertNotEqual(alice, host)
