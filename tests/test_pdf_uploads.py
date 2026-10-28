"""Real authenticated upload routes: preflight before parsing and database writes."""

import base64

import pytest

from src.config import settings
from tests.test_docx_uploads import upload_url
from tests_pdf.fixtures import ENCRYPTED_EMPTY, ENCRYPTED_LOCKED, image_pdf, pdf


@pytest.mark.parametrize("route", ["chat", "knowledge"])
@pytest.mark.parametrize(
    ("raw", "status"),
    [
        (b"not a PDF", 415),
        (pdf()[:-8], 415),
        (base64.b64decode(ENCRYPTED_EMPTY), 415),
        (base64.b64decode(ENCRYPTED_LOCKED), 415),
        (pdf(pages=201), 413),
        (pdf(content=b"0" * 100000, compressed=True), 413),
    ],
)
async def test_unsafe_pdf_is_rejected_before_extraction_and_db_commit(
    client, monkeypatch, tmp_path, route, raw, status
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    url = await upload_url(client, route)
    response = await client.post(
        url, files=[("files", ("synthetic.pdf", raw, "application/octet-stream"))]
    )
    assert response.status_code == status
    assert list(tmp_path.iterdir()) == []
    assert "Synthetic judgment" not in response.text
    if route == "chat":
        assert (await client.get(url)).json() == []
    else:
        assert (await client.get("/api/knowledge/verdicts")).json()["total"] == 0


@pytest.mark.parametrize("route", ["chat", "knowledge"])
async def test_text_pdf_is_accepted_and_unchanged(client, monkeypatch, tmp_path, route):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    raw = pdf()
    url = await upload_url(client, route)
    response = await client.post(
        url, files=[("files", ("synthetic.pdf", raw, "application/octet-stream"))]
    )
    assert response.status_code == (202 if route == "chat" else 200)
    assert len(list(tmp_path.iterdir())) == 1
    assert next(tmp_path.iterdir()).read_bytes() == raw
    if route == "chat":
        messages = (await client.get(url)).json()
        attachment = messages[0]["attachments"][0]
        assert attachment["page_count"] == 1
        assert attachment["extraction_status"] == "ok"
    else:
        assert response.json()["uploaded"] == 1


async def test_image_only_pdf_does_not_claim_successful_text_extraction(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    url = await upload_url(client, "chat")
    response = await client.post(
        url, files=[("files", ("scan.pdf", image_pdf(), "application/pdf"))]
    )
    assert response.status_code == 202
    messages = (await client.get(url)).json()
    attachment = messages[0]["attachments"][0]
    assert attachment["page_count"] == 1
    assert attachment["extraction_status"] == "empty"
