import asyncio
import importlib
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    page_count: int | None
    # ok | partial | empty | unsupported | error  (see db.models.EXTRACTION_STATUSES)
    status: str


def classify_pages(page_texts: list[str]) -> str:
    """'partial' when some pages have no text layer (typically scanned pages without OCR)."""
    if not page_texts:
        return "empty"
    with_text = sum(1 for t in page_texts if t.strip())
    if with_text == 0:
        return "empty"
    return "ok" if with_text == len(page_texts) else "partial"


def _read_text_file(path: Path) -> ExtractedDocument:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return ExtractedDocument(text, None, "ok" if text.strip() else "empty")


def _read_docx_file(path: Path) -> ExtractedDocument:
    docx = importlib.import_module("docx")
    document = docx.Document(str(path))
    text = "\n".join(p.text for p in document.paragraphs)
    return ExtractedDocument(text, None, "ok" if text.strip() else "empty")


def _read_pdf_file(path: Path) -> ExtractedDocument:
    pdfplumber = importlib.import_module("pdfplumber")
    pages: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            try:
                pages.append(page.extract_text() or "")
            except Exception:  # one broken page must not lose the whole document
                logger.warning(
                    "pdf page %s of %s could not be read", number, path.name, exc_info=True
                )
                pages.append("")
    return ExtractedDocument("\n".join(pages), len(pages), classify_pages(pages))


_READERS = {
    ".txt": _read_text_file,
    ".md": _read_text_file,
    ".docx": _read_docx_file,
    ".pdf": _read_pdf_file,
}


async def extract_document(path: Path) -> ExtractedDocument:
    reader = _READERS.get(path.suffix.lower())
    if reader is None:
        return ExtractedDocument("", None, "unsupported")
    try:
        return await asyncio.to_thread(reader, path)
    except Exception:
        # Previously errors silently became "" — now they are logged and visible as status=error.
        logger.exception("text extraction failed for %s", path.name)
        return ExtractedDocument("", None, "error")


async def extract_text_from_file(path: Path) -> str:
    """Backward-compatible helper used by the knowledge-base upload."""
    return (await extract_document(path)).text
