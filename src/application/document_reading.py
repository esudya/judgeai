"""Read a supported document through an adapter; never return raw parser diagnostics."""

from typing import Protocol

from src.domain.documents import MAX_TEXT_CHARACTERS, ExtractedDocument
from src.domain.uploads import UploadRejected


class DocumentReader(Protocol):
    def __call__(self) -> ExtractedDocument: ...


class ReadDocument:
    def execute(self, reader: DocumentReader | None) -> ExtractedDocument:
        if reader is None:
            return ExtractedDocument("", None, "unsupported", ("unsupported_format",))
        try:
            document = reader()
            if len(document.text) > MAX_TEXT_CHARACTERS:
                return ExtractedDocument("", None, "error", ("resource_limit",))
            return document
        except UploadRejected as exc:
            issue = "resource_limit" if exc.code.endswith("_limit") else "invalid_document"
            return ExtractedDocument("", None, "error", (issue,))
        except Exception:
            return ExtractedDocument("", None, "error", ("invalid_document",))
