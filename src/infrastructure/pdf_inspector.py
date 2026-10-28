"""Strict bounded PDF inspection, invoked only in a resource-limited worker."""

import math
import re
from typing import BinaryIO
from weakref import WeakKeyDictionary

from src.domain.uploads import PdfInspection, PdfLimits, reject_pdf, require_pdf_budget


def check_pdf_frame(source: BinaryIO, limits: PdfLimits) -> None:
    source.seek(0, 2)
    size = source.tell()
    require_pdf_budget(size, limits.max_source_bytes)
    source.seek(0)
    if not re.match(rb"%PDF-(?:1\.[0-7]|2\.0)(?:\r\n|\r|\n)", source.read(16)):
        raise reject_pdf("pdf_invalid")
    source.seek(max(0, size - 4096))
    end = re.search(rb"startxref\s+(\d+)\s+%%EOF\s*$", source.read(4096))
    if end is None or int(end[1]) >= size:
        raise reject_pdf("pdf_invalid")
    source.seek(0)


def inspect_pdf(source: BinaryIO, limits: PdfLimits) -> PdfInspection:
    check_pdf_frame(source, limits)
    try:
        from pdfminer import settings
        from pdfminer.pdfdocument import PDFDocument, PDFEncryptionError
        from pdfminer.pdfparser import PDFParser
        from pdfminer.pdftypes import PDFObjRef, PDFStream, resolve1
        from pdfminer.psparser import literal_name
    except ImportError:
        raise reject_pdf("pdf_unavailable") from None

    raw_sizes = WeakKeyDictionary()

    class BoundedParser(PDFParser):
        def do_keyword(self, pos, token):
            super().do_keyword(pos, token)
            if token is self.KEYWORD_STREAM:
                start, value = self.curstack[-1]
                raw_size = len(value.rawdata)
                boundary = self.bufpos + self.charpos
                gap = boundary - start - raw_size
                if gap not in (0, 1, 2):
                    raise reject_pdf("pdf_invalid")
                position = self.fp.tell()
                try:
                    self.fp.seek(start + raw_size)
                    separator = self.fp.read(gap)
                    if separator not in (b"", b"\n", b"\r", b"\r\n"):
                        raise reject_pdf("pdf_invalid")
                    if self.fp.read(9) != b"endstream":
                        raise reject_pdf("pdf_invalid")
                    if self.fp.read(1) not in (b" ", b"\t", b"\r", b"\n", b"\x00", b"\x0c"):
                        raise reject_pdf("pdf_invalid")
                finally:
                    self.fp.seek(position)
                raw_sizes[value] = raw_size

    strict = settings.STRICT
    settings.STRICT = True
    try:
        document = PDFDocument(BoundedParser(source), fallback=False)
        if document.encryption is not None:
            raise reject_pdf("pdf_encrypted")
        ids = set()
        for xref in document.xrefs:
            for identity in xref.get_objids():
                ids.add(identity)
                require_pdf_budget(len(ids), limits.max_objects)
        if not ids:
            raise reject_pdf("pdf_invalid")
        nodes = 0
        decoded_bytes = 0

        def walk(value, depth=0):
            nonlocal nodes, decoded_bytes
            nodes += 1
            require_pdf_budget(nodes, limits.max_nodes)
            require_pdf_budget(depth, limits.max_depth)
            if isinstance(value, PDFObjRef):
                if value.objid not in ids:
                    raise reject_pdf("pdf_invalid")
            elif isinstance(value, PDFStream):
                walk(value.attrs, depth + 1)
                require_pdf_budget(len(value.get_filters()), limits.max_filters)
                raw_size = raw_sizes[value]
                data = value.get_data()
                size = len(data)
                require_pdf_budget(size, limits.max_stream_bytes)
                decoded_bytes += size
                require_pdf_budget(decoded_bytes, limits.max_total_decoded_bytes)
                require_pdf_budget(size, raw_size * limits.max_ratio)
                if (
                    value.attrs.get("Subtype") is not None
                    and literal_name(value.attrs["Subtype"]) == "Image"
                ):
                    width = resolve1(value.attrs.get("Width"))
                    height = resolve1(value.attrs.get("Height"))
                    if type(width) is not int or type(height) is not int or min(width, height) <= 0:
                        raise reject_pdf("pdf_invalid")
                    require_pdf_budget(width * height, limits.max_image_pixels)
            elif isinstance(value, dict):
                for child in value.values():
                    walk(child, depth + 1)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    walk(child, depth + 1)

        for identity in ids:
            walk(document.getobj(identity))

        visited = set()

        def pages(reference, depth=0, inherited_box=None):
            require_pdf_budget(depth, limits.max_depth)
            if not isinstance(reference, PDFObjRef) or reference.objid in visited:
                raise reject_pdf("pdf_invalid")
            visited.add(reference.objid)
            node = resolve1(reference)
            if not isinstance(node, dict):
                raise reject_pdf("pdf_invalid")
            kind = literal_name(node.get("Type"))
            box = node.get("MediaBox", inherited_box)
            if kind == "Pages":
                declared = resolve1(node.get("Count"))
                children = resolve1(node.get("Kids"))
                if type(declared) is not int or declared < 0 or not isinstance(children, list):
                    raise reject_pdf("pdf_invalid")
                require_pdf_budget(declared, limits.max_pages)
                count = 0
                for child in children:
                    count += pages(child, depth + 1, box)
                    require_pdf_budget(count, limits.max_pages)
                if declared != count:
                    raise reject_pdf("pdf_invalid")
                return count
            if kind != "Page":
                raise reject_pdf("pdf_invalid")
            rectangle = resolve1(box)
            if not isinstance(rectangle, list) or len(rectangle) != 4:
                raise reject_pdf("pdf_invalid")
            coordinates = [resolve1(item) for item in rectangle]
            unit = resolve1(node.get("UserUnit", 1))
            if any(
                type(item) not in (int, float) or not math.isfinite(item)
                for item in coordinates + [unit]
            ):
                raise reject_pdf("pdf_invalid")
            width, height = coordinates[2] - coordinates[0], coordinates[3] - coordinates[1]
            if min(width, height, unit) <= 0:
                raise reject_pdf("pdf_invalid")
            require_pdf_budget(max(width, height) * unit, limits.max_page_points)
            return 1

        count = pages(document.catalog.get("Pages"))
        if count == 0:
            raise reject_pdf("pdf_invalid")
        return PdfInspection(count, len(ids), decoded_bytes)
    except PDFEncryptionError:
        raise reject_pdf("pdf_encrypted") from None
    except (MemoryError, RecursionError):
        raise reject_pdf("pdf_limit") from None
    except Exception as exc:
        from src.domain.uploads import UploadRejected

        if isinstance(exc, UploadRejected):
            raise
        raise reject_pdf("pdf_invalid") from None
    finally:
        settings.STRICT = strict
