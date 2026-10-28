"""Document reading results and user-safe diagnostics, independent of parsers and HTTP."""

from dataclasses import dataclass

MAX_TEXT_CHARACTERS = 2_000_000
MAX_TEXT_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    page_count: int | None
    status: str
    issues: tuple[str, ...] = ()
    unread_pages: tuple[int, ...] = ()
    encoding: str | None = None


def classify_pages(page_texts: list[str]) -> str:
    if not page_texts:
        return "empty"
    count = sum(bool(text.strip()) for text in page_texts)
    return "empty" if count == 0 else "ok" if count == len(page_texts) else "partial"


_MESSAGES = {
    "unsupported_format": "This file variant is unsupported. Convert it to TXT, DOCX or PDF.",
    "invalid_encoding": "Text encoding is invalid or ambiguous. Save the file as UTF-8.",
    "binary_text": "The file contains binary data rather than supported plain text.",
    "resource_limit": "The document exceeds the supported reading limits.",
    "no_text_layer": "Some PDF pages have no readable text. OCR or another copy is required.",
    "unreadable_pages": "Some PDF pages could not be read. Provide another copy.",
    "unsupported_content": "Images or embedded content were not read; document text is incomplete.",
    "tracked_changes": "The document contains tracked changes. Review a finalized copy.",
    "invalid_document": "The document is damaged, encrypted or unsupported.",
    "empty_document": "No usable text was found in this document.",
}


def reading_warnings(document: ExtractedDocument) -> list[str]:
    messages = [_MESSAGES[issue] for issue in document.issues if issue in _MESSAGES]
    if document.unread_pages:
        messages.append("Unread pages: " + ", ".join(map(str, document.unread_pages)))
    return messages


class UnreadableInput(ValueError):
    """No document text or question can ground an analysis."""
