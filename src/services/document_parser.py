import asyncio
import importlib
from pathlib import Path


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_docx_file(path: Path) -> str:
    try:
        docx = importlib.import_module("docx")
    except ModuleNotFoundError:
        return ""

    try:
        document = docx.Document(str(path))
        paragraphs = getattr(document, "paragraphs", [])
        return "\n".join(getattr(paragraph, "text", "") for paragraph in paragraphs)
    except Exception:
        return ""


def _read_pdf_file(path: Path) -> str:
    try:
        pdfplumber = importlib.import_module("pdfplumber")
    except ModuleNotFoundError:
        return ""

    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = []

            for page in pdf.pages:
                try:
                    pages.append(page.extract_text() or "")
                except Exception:
                    continue

            return "\n".join(pages)
    except Exception:
        return ""


async def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md"}:
        return await asyncio.to_thread(_read_text_file, path)

    if suffix == ".docx":
        return await asyncio.to_thread(_read_docx_file, path)

    if suffix == ".pdf":
        return await asyncio.to_thread(_read_pdf_file, path)

    return ""
