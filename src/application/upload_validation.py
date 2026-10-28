"""Upload admission use case, independent of HTTP, storage paths and ZIP libraries."""

from typing import BinaryIO, Protocol

from src.domain.uploads import (
    DocxInspection,
    DocxLimits,
    PdfInspection,
    PdfLimits,
    reject_pdf,
)


class DocxInspectionPort(Protocol):
    def inspect(self, source: BinaryIO, limits: DocxLimits) -> DocxInspection: ...


class PdfInspectionPort(Protocol):
    def inspect(self, source: BinaryIO, limits: PdfLimits) -> PdfInspection: ...


class ValidateUpload:
    def __init__(
        self,
        inspector: DocxInspectionPort,
        limits: DocxLimits,
        *,
        pdf_inspector: PdfInspectionPort | None = None,
        pdf_limits: PdfLimits | None = None,
    ):
        self.inspector = inspector
        self.limits = limits
        self.pdf_inspector = pdf_inspector
        self.pdf_limits = pdf_limits

    def execute(self, source: BinaryIO, suffix: str) -> DocxInspection | PdfInspection | None:
        if suffix.lower() == ".pdf":
            if self.pdf_inspector is None or self.pdf_limits is None:
                raise reject_pdf("pdf_unavailable")
            inspector, limits = self.pdf_inspector, self.pdf_limits
        elif suffix.lower() == ".docx":
            inspector, limits = self.inspector, self.limits
        else:
            return None
        position = source.tell()
        try:
            return inspector.inspect(source, limits)
        finally:
            source.seek(position)
