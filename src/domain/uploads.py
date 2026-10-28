"""Pure admission policy for the supported, bounded DOCX package subset."""

from dataclasses import dataclass, fields


class UploadRejected(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class DocxLimits:
    max_compressed_bytes: int = 50 * 1024 * 1024
    max_entries: int = 512
    max_directory_bytes: int = 256 * 1024
    max_total_bytes: int = 100 * 1024 * 1024
    max_member_bytes: int = 20 * 1024 * 1024
    max_xml_bytes: int = 8 * 1024 * 1024
    max_ratio: int = 200
    max_xml_depth: int = 128
    max_xml_elements: int = 200000

    def __post_init__(self):
        if any(
            type(getattr(self, item.name)) is not int or getattr(self, item.name) <= 0
            for item in fields(self)
        ):
            raise ValueError("DOCX limits must be positive integers")


@dataclass(frozen=True)
class ArchiveEntry:
    name: str
    size: int
    compressed_size: int
    method: int
    encrypted: bool
    symlink: bool
    zip_version: int


@dataclass(frozen=True)
class DocxInspection:
    entries: int
    uncompressed_bytes: int


def require_budget(value: int, maximum: int) -> None:
    if value > maximum:
        raise UploadRejected("docx_limit", "DOCX exceeds the supported processing limits")


def check_directory(entries: int, directory_bytes: int, source_bytes: int, limits: DocxLimits):
    require_budget(source_bytes, limits.max_compressed_bytes)
    require_budget(entries, limits.max_entries)
    require_budget(directory_bytes, limits.max_directory_bytes)


def check_entry(entry: ArchiveEntry, limits: DocxLimits):
    name = entry.name
    parts = name.rstrip("/").split("/")
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or ":" in name
        or any(ord(character) < 32 for character in name)
        or any(part in {"", ".", ".."} for part in parts)
        or entry.symlink
    ):
        raise UploadRejected("docx_unsafe", "DOCX contains unsafe package entries")
    if entry.encrypted or entry.method not in {0, 8} or entry.zip_version > 20:
        raise UploadRejected("docx_unsupported", "DOCX encryption or compression is unsupported")
    if name.lower().endswith("vbaproject.bin"):
        raise UploadRejected("docx_unsafe", "Macro-enabled documents are unsupported")
    if entry.size < 0 or entry.compressed_size < 0:
        raise UploadRejected("docx_invalid", "DOCX package is invalid")
    require_budget(entry.size, limits.max_member_bytes)
    require_budget(entry.size, entry.compressed_size * limits.max_ratio)
    if name.lower().endswith((".xml", ".rels")):
        require_budget(entry.size, limits.max_xml_bytes)
