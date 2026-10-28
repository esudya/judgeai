"""Bounded plain text and static Word XML adapters; no converters or macro execution."""

import codecs
import unicodedata
from pathlib import Path

from src.domain.documents import MAX_TEXT_BYTES, MAX_TEXT_CHARACTERS, ExtractedDocument


def _text_result(text: str, encoding: str) -> ExtractedDocument:
    if len(text) > MAX_TEXT_CHARACTERS:
        return ExtractedDocument("", None, "error", ("resource_limit",))
    if any(unicodedata.category(char) == "Cc" and char not in "\t\n\r\f" for char in text):
        return ExtractedDocument("", None, "error", ("binary_text",))
    return ExtractedDocument(
        text,
        None,
        "ok" if text.strip() else "empty",
        () if text.strip() else ("empty_document",),
        encoding=encoding,
    )


def read_text(path: Path) -> ExtractedDocument:
    with path.open("rb") as source:
        raw = source.read(MAX_TEXT_BYTES + 1)
    if len(raw) > MAX_TEXT_BYTES:
        return ExtractedDocument("", None, "error", ("resource_limit",))
    if raw.startswith((b"PK\x03\x04", b"%PDF-", b"\xd0\xcf\x11\xe0", b"{\\rtf")):
        return ExtractedDocument("", None, "error", ("binary_text",))
    encoding = "utf-8-sig"
    if raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        encoding = "utf-32"
    elif raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        encoding = "utf-16"
    try:
        text = raw.decode(encoding, errors="strict")
    except UnicodeDecodeError as exc:
        prefix = (
            raw[: exc.start].decode("utf-8", errors="strict") if encoding == "utf-8-sig" else ""
        )
        if (
            encoding != "utf-8-sig"
            or raw.startswith(codecs.BOM_UTF8)
            or any(ord(char) > 127 for char in prefix)
        ):
            return ExtractedDocument("", None, "error", ("invalid_encoding",))
        try:
            text = raw.decode("cp1251", errors="strict")
        except UnicodeError:
            return ExtractedDocument("", None, "error", ("invalid_encoding",))
        if len(text) > MAX_TEXT_CHARACTERS:
            return ExtractedDocument("", None, "error", ("resource_limit",))
        letters = [char for char in text if char.isalpha()]
        cyrillic = sum("А" <= char <= "я" or char in "Ёё" for char in letters)
        if cyrillic < 4 or cyrillic < len(letters) * 0.8:
            return ExtractedDocument("", None, "error", ("invalid_encoding",))
        encoding = "cp1251"
    return _text_result(text, encoding)
