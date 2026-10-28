"""Upload admission use case, independent of HTTP, storage paths and ZIP libraries."""

from typing import BinaryIO, Protocol

from src.domain.uploads import DocxInspection, DocxLimits


class DocxInspectionPort(Protocol):
    def inspect(self, source: BinaryIO, limits: DocxLimits) -> DocxInspection: ...


class ValidateUpload:
    def __init__(self, inspector: DocxInspectionPort, limits: DocxLimits):
        self.inspector = inspector
        self.limits = limits

    def execute(self, source: BinaryIO, suffix: str) -> DocxInspection | None:
        if suffix.lower() != ".docx":
            return None
        position = source.tell()
        try:
            return self.inspector.inspect(source, self.limits)
        finally:
            source.seek(position)
