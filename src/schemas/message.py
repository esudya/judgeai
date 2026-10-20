from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str | None
    size: int


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    role: str
    content: str | None
    status: str
    analysis: dict | None
    error: str | None
    created_at: datetime
    attachments: list[AttachmentRead]


class MessageSendResponse(BaseModel):
    user_message: MessageRead
    assistant_message: MessageRead
