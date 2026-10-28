import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi import UploadFile

from src.services.file_reader import save_upload_file, settings
from tests_uploads_http.test_upload_admission import app


class PdfAdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_renamed_pdf_is_rejected_and_removed_before_extraction(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(settings, "UPLOAD_DIR", directory),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/upload", files={"file": ("synthetic.pdf", b"not a PDF", "application/pdf")}
                )
            self.assertEqual(response.status_code, 415)
            self.assertEqual(list(Path(directory).iterdir()), [])

    async def test_text_upload_still_preserves_bytes(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(settings, "UPLOAD_DIR", directory),
        ):
            path, size = await save_upload_file(
                UploadFile(io.BytesIO(b"Synthetic"), filename="a.txt")
            )
            self.assertEqual(path.read_bytes(), b"Synthetic")
            self.assertEqual(size, 9)

    async def test_real_pdf_bytes_preserved_or_platform_refused(self):
        import sys

        from tests_pdf.fixtures import pdf

        raw = pdf()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(settings, "UPLOAD_DIR", directory),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/upload", files={"file": ("synthetic.PDF", raw, "application/octet-stream")}
                )
            if sys.platform == "linux":
                self.assertEqual(response.status_code, 200)
                self.assertEqual((Path(directory) / response.json()["name"]).read_bytes(), raw)
            else:
                self.assertEqual(response.status_code, 503)
                self.assertEqual(list(Path(directory).iterdir()), [])

    async def test_unavailable_and_busy_inspectors_return_503_without_leaving_files(self):
        from src.domain.uploads import reject_pdf
        from tests_pdf.fixtures import pdf

        for code in ("pdf_busy", "pdf_unavailable"):
            with (
                tempfile.TemporaryDirectory() as directory,
                patch.object(settings, "UPLOAD_DIR", directory),
                patch(
                    "src.services.file_reader.PdfProcessInspector.inspect",
                    side_effect=reject_pdf(code),
                ),
            ):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/upload", files={"file": ("synthetic.pdf", pdf(), "application/pdf")}
                    )
                self.assertEqual(response.status_code, 503)
                self.assertEqual(list(Path(directory).iterdir()), [])

    async def test_resource_rejection_returns_413_and_cleans_the_upload(self):
        from src.domain.uploads import reject_pdf
        from tests_pdf.fixtures import pdf

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(settings, "UPLOAD_DIR", directory),
            patch(
                "src.services.file_reader.PdfProcessInspector.inspect",
                side_effect=reject_pdf("pdf_limit"),
            ),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/upload", files={"file": ("synthetic.pdf", pdf(), "application/pdf")}
                )
            self.assertEqual(response.status_code, 413)
            self.assertEqual(list(Path(directory).iterdir()), [])
