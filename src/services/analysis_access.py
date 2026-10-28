"""Authorization-independent request/result identity check for queued jobs."""

from typing import Protocol


class JobMessage(Protocol):
    id: int
    chat_id: int
    role: str
    status: str
    request_message_id: int | None


def is_pending_reply(request: JobMessage, result: JobMessage) -> bool:
    return (
        request.role == "user"
        and result.role == "assistant"
        and request.chat_id == result.chat_id
        and result.request_message_id == request.id
        and result.status == "pending"
    )
