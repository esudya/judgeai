"""Bounded plain text and static Word XML adapters; no converters or macro execution."""

import codecs
import unicodedata
import zipfile
from pathlib import Path
from xml.parsers import expat

from src.domain.documents import MAX_TEXT_BYTES, MAX_TEXT_CHARACTERS, ExtractedDocument
from src.domain.uploads import DocxLimits, UploadRejected
from src.infrastructure.docx_inspector import DocxInspector

_WORD_NAMESPACES = {
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
}


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
    except UnicodeError:
        if encoding != "utf-8-sig":
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


def read_word(path: Path) -> ExtractedDocument:
    with path.open("rb") as source:
        DocxInspector().inspect(source, DocxLimits())
        source.seek(0)
        with zipfile.ZipFile(source) as package:
            parts = ["word/document.xml"] + sorted(
                name
                for name in package.namelist()
                if name.startswith("word/")
                and name.endswith(".xml")
                and (
                    name.startswith(("word/header", "word/footer"))
                    or name in {"word/footnotes.xml", "word/endnotes.xml"}
                )
            )
            output: list[str] = []
            issues: set[str] = set()
            size = 0
            stack: list[str] = []
            for part in parts:
                parser = expat.ParserCreate(namespace_separator="}")

                def append(text):
                    nonlocal size
                    size += len(text)
                    if size > MAX_TEXT_CHARACTERS:
                        raise UploadRejected("reading_limit", "Document text is too large")
                    output.append(text)

                def start(name, attrs):
                    namespace, _, local = name.rpartition("}")
                    tag = local if namespace in _WORD_NAMESPACES else "foreign"
                    stack.append(tag)
                    if tag in {"drawing", "pict", "object", "altChunk", "sym", "subDoc"} or (
                        namespace not in _WORD_NAMESPACES
                        and local in {"AlternateContent", "oMath", "oMathPara"}
                    ):
                        issues.add("unsupported_content")
                    if tag in {"ins", "del", "moveFrom", "moveTo"}:
                        issues.add("tracked_changes")
                    if tag in {"tab", "br", "cr"} and "del" not in stack:
                        append("\t" if tag == "tab" else "\n")

                def end(name):
                    if stack[-1] == "p":
                        append("\n")
                    stack.pop()

                def content(text):
                    if stack[-1:] == ["t"] and not {"del", "moveFrom"}.intersection(stack):
                        append(text)

                parser.StartElementHandler = start
                parser.EndElementHandler = end
                parser.CharacterDataHandler = content
                parser.Parse(package.read(part), True)
    text = "".join(output).strip()
    status = "empty" if not text else "partial" if issues else "ok"
    if not text:
        issues.add("empty_document")
    return ExtractedDocument(text, None, status, tuple(sorted(issues)))
