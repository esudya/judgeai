"""DOCX admission through real authenticated routes and PostgreSQL rollback."""

import io

import pytest
from docx import Document

from src.config import settings
from tests_uploads.test_docx_guard import archive


async def upload_url(client, route):
    if route == "knowledge":
        return "/api/knowledge/verdicts/upload"
    chat = await client.post("/api/chats", json={"title": "Synthetic upload acceptance"})
    assert chat.status_code == 201
    return f"/api/chats/{chat.json()['id']}/messages"


@pytest.mark.parametrize("route", ["chat", "knowledge"])
@pytest.mark.parametrize(
    ("payload", "status"),
    [
        (b"not a DOCX", 415),
        (archive(extra=[("word/media/bomb.bin", b"0" * 200000)]), 413),
        (archive(extra=[("word/comments.xml", b'<!DOCTYPE x [<!ENTITY a "x">]><x>&a;</x>')]), 415),
    ],
)
async def test_rejected_docx_removes_file_and_does_not_commit_rows(
    client, monkeypatch, tmp_path, route, payload, status
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    url = await upload_url(client, route)
    response = await client.post(
        url, files=[("files", ("synthetic.docx", payload, "application/octet-stream"))]
    )
    assert response.status_code == status
    assert list(tmp_path.iterdir()) == []
    if route == "chat":
        assert (await client.get(url)).json() == []
    else:
        assert (await client.get("/api/knowledge/verdicts")).json()["total"] == 0


@pytest.mark.parametrize("route", ["chat", "knowledge"])
async def test_real_docx_is_accepted_and_original_bytes_preserved(
    client, monkeypatch, tmp_path, route
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    document = Document()
    document.add_paragraph("Synthetic judgment: no personal data.")
    output = io.BytesIO()
    document.save(output)
    raw = output.getvalue()
    url = await upload_url(client, route)
    response = await client.post(
        url, files=[("files", ("synthetic.docx", raw, "application/octet-stream"))]
    )
    assert response.status_code == (202 if route == "chat" else 200)
    assert len(list(tmp_path.iterdir())) == 1
    assert next(tmp_path.iterdir()).read_bytes() == raw
    if route == "chat":
        assert response.json()["user_message"]["attachments"][0]["size"] == len(raw)
    else:
        assert response.json()["uploaded"] == 1
