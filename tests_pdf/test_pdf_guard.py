import base64
import io
import re
import unittest
from dataclasses import replace

from src.application.upload_validation import ValidateUpload
from src.domain.uploads import DocxLimits, PdfLimits, UploadRejected
from src.infrastructure.pdf_inspector import inspect_pdf
from tests_pdf.fixtures import (
    ENCRYPTED_EMPTY,
    ENCRYPTED_LOCKED,
    image_pdf,
    package,
    pdf,
    stream,
    xref_stream_pdf,
)


class PdfGuardTests(unittest.TestCase):
    def inspect(self, raw, limits=None):
        return inspect_pdf(io.BytesIO(raw), limits or PdfLimits())

    def test_text_and_image_only_documents_are_supported_without_extracting_text(self):
        for raw, pages in [(pdf(), 1), (pdf(pages=2, compressed=True), 2), (image_pdf(), 1)]:
            result = self.inspect(raw)
            self.assertEqual(result.pages, pages)
            self.assertGreater(result.objects, 0)
            self.assertGreater(result.decoded_bytes, 0)

    def test_renamed_header_only_truncated_and_invalid_xref_are_rejected(self):
        raw = pdf()
        malformed = re.sub(rb"startxref\n\d+", b"startxref\n1", raw)
        for content in (b"not a PDF", b"%PDF-1.7\n%%EOF", raw[:-8], malformed, raw + b"hidden"):
            with self.subTest(content=content[:12]), self.assertRaises(UploadRejected) as error:
                self.inspect(content)
            self.assertEqual(error.exception.code, "pdf_invalid")

    def test_empty_password_and_locked_encryption_are_both_rejected(self):
        for fixture in (ENCRYPTED_EMPTY, ENCRYPTED_LOCKED):
            with self.assertRaises(UploadRejected) as error:
                self.inspect(base64.b64decode(fixture))
            self.assertEqual(error.exception.code, "pdf_encrypted")

    def test_actual_page_count_limit_and_exact_boundary(self):
        self.assertEqual(self.inspect(pdf(pages=2), replace(PdfLimits(), max_pages=2)).pages, 2)
        with self.assertRaises(UploadRejected) as error:
            self.inspect(pdf(pages=3), replace(PdfLimits(), max_pages=2))
        self.assertEqual(error.exception.code, "pdf_limit")

    def test_lied_page_count_missing_pages_and_cycles_are_invalid(self):
        bad = [
            pdf(pages=2).replace(b"/Count 2", b"/Count 1"),
            pdf(pages=0),
            package([b"<< /Type /Catalog >>"]),
            package(
                [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [2 0 R] /Count 1 >>"]
            ),
        ]
        for raw in bad:
            with self.subTest(raw=raw[:15]), self.assertRaises(UploadRejected):
                self.inspect(raw)

    def test_source_object_and_decoded_stream_limits(self):
        cases = [
            (pdf(), replace(PdfLimits(), max_source_bytes=100)),
            (pdf(), replace(PdfLimits(), max_objects=4)),
            (pdf(content=b"0" * 2000), replace(PdfLimits(), max_stream_bytes=1000)),
            (pdf(pages=2, content=b"0" * 800), replace(PdfLimits(), max_total_decoded_bytes=1500)),
            (pdf(content=b"0" * 10000, compressed=True), replace(PdfLimits(), max_ratio=10)),
        ]
        for raw, limits in cases:
            with self.subTest(limits=limits), self.assertRaises(UploadRejected) as error:
                self.inspect(raw, limits)
            self.assertEqual(error.exception.code, "pdf_limit")

    def test_unreferenced_bomb_and_corrupt_streams_are_not_ignored(self):
        with self.assertRaises(UploadRejected):
            self.inspect(
                pdf(extra=[stream(b"0" * 100000, compressed=True)]),
                replace(PdfLimits(), max_ratio=10),
            )
        with self.assertRaises(UploadRejected) as error:
            self.inspect(
                pdf(extra=[b"<< /Length 4 /Filter /FlateDecode >>\nstream\nxxxx\nendstream"])
            )
        self.assertEqual(error.exception.code, "pdf_invalid")
        self.assertNotIn("xxxx", str(error.exception))

    def test_broken_indirect_references_and_bad_geometry_are_rejected(self):
        for raw in (
            pdf(extra=[b"<< /Unknown 999 0 R >>"]),
            pdf(box=b"[0 0 0 792]"),
            pdf(box=b"[0 0 999999 792]"),
        ):
            with self.assertRaises(UploadRejected):
                self.inspect(raw)

    def test_inline_depth_node_and_filter_limits(self):
        for extra, limits in [
            (b"[" * 20 + b"0" + b"]" * 20, replace(PdfLimits(), max_depth=10)),
            (b"[" + b"0 " * 500 + b"]", replace(PdfLimits(), max_nodes=100)),
            (
                stream(
                    b"x",
                    attrs=(b"/Filter [" + b"/ASCIIHexDecode " * 5 + b"]"),
                ),
                PdfLimits(),
            ),
        ]:
            with self.subTest(limits=limits), self.assertRaises(UploadRejected) as error:
                self.inspect(pdf(extra=[extra]), limits)
            self.assertEqual(error.exception.code, "pdf_limit")

    def test_positive_integer_limits_are_required(self):
        for value in (0, -1, True, "100"):
            with self.assertRaises(ValueError):
                PdfLimits(max_pages=value)

    def test_application_preserves_position_on_pdf_success_and_failure(self):
        class NeverDocx:
            def inspect(self, source, limits):
                raise AssertionError("DOCX inspector used for PDF")

        class PdfPort:
            def inspect(self, source, limits):
                source.seek(0)
                return inspect_pdf(source, limits)

        validator = ValidateUpload(
            NeverDocx(), DocxLimits(), pdf_inspector=PdfPort(), pdf_limits=PdfLimits()
        )
        for raw in (pdf(), b"invalid"):
            source = io.BytesIO(raw)
            source.seek(3)
            try:
                validator.execute(source, ".PDF")
            except UploadRejected:
                pass
            self.assertEqual(source.tell(), 3)

    def test_pdf_cannot_silently_skip_a_missing_inspector(self):
        with self.assertRaises(UploadRejected) as error:
            ValidateUpload(None, DocxLimits()).execute(io.BytesIO(pdf()), ".pdf")
        self.assertEqual(error.exception.code, "pdf_unavailable")


class PdfCompatibilityTests(unittest.TestCase):
    def test_cross_reference_stream_is_supported(self):
        result = inspect_pdf(io.BytesIO(xref_stream_pdf()), PdfLimits())
        self.assertEqual(result.pages, 1)
        self.assertEqual(result.objects, 6)
