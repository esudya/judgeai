import logging
from datetime import datetime

from pydantic import BaseModel, ConfigDict, ValidationError, computed_field

from src.schemas.analysis import CaseAnalysis

logger = logging.getLogger(__name__)


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str | None
    size: int
    page_count: int | None = None
    extraction_status: str = "ok"


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    role: str
    content: str | None
    status: str
    stage: str | None = None
    # Raw JSON as stored (kept for backward compatibility with pre-0.4 clients).
    analysis: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime | None = None
    attachments: list[AttachmentRead]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def result(self) -> CaseAnalysis | None:
        """Typed analysis; None for legacy (pre-0.4) analyses and for unreadable data."""
        if not self.analysis or "schema_version" not in self.analysis:
            return None
        try:
            return CaseAnalysis.model_validate(self.analysis)
        except ValidationError:
            logger.warning("message %s has an analysis that no longer matches the schema", self.id)
            return None


class MessageSendResponse(BaseModel):
    user_message: MessageRead
    assistant_message: MessageRead
