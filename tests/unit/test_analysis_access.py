import unittest
from types import SimpleNamespace

from src.services.analysis_access import is_pending_reply


class AnalysisPairTests(unittest.TestCase):
    def test_same_chat_different_request_cannot_overwrite_result(self):
        request = SimpleNamespace(id=10, chat_id=1, role="user")
        result = SimpleNamespace(
            request_message_id=9, chat_id=1, role="assistant", status="pending"
        )
        self.assertFalse(is_pending_reply(request, result))
        result.request_message_id = 10
        self.assertTrue(is_pending_reply(request, result))
        for status in ("running", "completed", "failed"):
            result.status = status
            self.assertFalse(is_pending_reply(request, result))

    def test_other_chat_or_wrong_roles_are_rejected(self):
        request = SimpleNamespace(id=10, chat_id=1, role="user")
        result = SimpleNamespace(
            request_message_id=10, chat_id=2, role="assistant", status="pending"
        )
        self.assertFalse(is_pending_reply(request, result))
        result.chat_id = 1
        result.role = "user"
        self.assertFalse(is_pending_reply(request, result))
