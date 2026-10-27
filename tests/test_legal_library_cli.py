from argparse import Namespace
from datetime import UTC, date, datetime
from hashlib import sha256

import pytest
from sqlalchemy import select

from src.cli.legal_library import prepare, read_source, run_import
from src.db.models import LegalEdition, LegalProvision
from src.db.session import async_session_factory
from src.schemas.legal_library import SnapshotImport


def args_for(tmp_path, source_format, raw):
    source = tmp_path / "fixture.source"
    source.write_bytes(raw)
    return Namespace(
        source=source,
        manifest=tmp_path / "fixture.json",
        format=source_format,
        key="synthetic-cli",
        title="Synthetic CLI fixture",
        kind="code",
        number="test",
        adopted_on=date(2020, 1, 1),
        source_url="https://pravo.gov.ru/synthetic-fixture",
        edition_label="Unreviewed synthetic fixture",
        retrieved_at=datetime(2026, 10, 28, tzinfo=UTC),
    )


async def test_prepare_and_import_constitution_html_preserves_source(tmp_path):
    raw = (
        '<body><div itemprop="articleBody"><h3>Статья 1</h3><p>Synthetic rule.</p></div></body>'
    ).encode()
    args = args_for(tmp_path, "kremlin", raw)
    prepare(args)
    await run_import(args)
    await run_import(args)
    async with async_session_factory() as db:
        edition = await db.scalar(select(LegalEdition))
        provision = await db.scalar(select(LegalProvision))
        assert edition.source_bytes == raw
        assert edition.source_sha256 == sha256(raw).hexdigest()
        assert provision.locator == "article.1"
        assert provision.body == "Статья 1\nSynthetic rule."


def test_prepare_pravo_export_has_real_article_text(tmp_path):
    raw = (
        b'MIME-Version: 1.0\r\nContent-Type: multipart/related; boundary="boundary"\r\n\r\n'
        b"--boundary\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
        + "<body><p>Статья 1. Synthetic title</p><p>Synthetic rule.</p></body>".encode()
        + b"\r\n--boundary--\r\n"
    )
    args = args_for(tmp_path, "pravo-export", raw)
    prepare(args)
    manifest = SnapshotImport.model_validate_json(args.manifest.read_text())
    assert manifest.provisions[0].locator == "article.1"
    assert "Synthetic rule." in manifest.provisions[0].body


def synthetic_pdf():
    stream = b"BT /F1 12 Tf 72 720 Td (Synthetic rule.) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(i).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    for offset in offsets:
        data += f"{offset:010} 00000 n \n".encode()
    return (
        data
        + b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref).encode()
        + b"\n%%EOF\n"
    )


def test_prepare_pdf_preserves_page_coordinates(tmp_path):
    args = args_for(tmp_path, "pdf", synthetic_pdf())
    prepare(args)
    manifest = SnapshotImport.model_validate_json(args.manifest.read_text())
    assert manifest.provisions[0].body == "Synthetic rule."
    assert manifest.provisions[0].start_page == manifest.provisions[0].end_page == 1
    assert manifest.raw_sha256 == sha256(args.source.read_bytes()).hexdigest()


def test_prepare_cannot_overwrite_source_archive(tmp_path):
    args = args_for(tmp_path, "kremlin", b"Keep original bytes")
    args.manifest = args.source
    with pytest.raises(ValueError, match="overwrite"):
        prepare(args)
    assert args.source.read_bytes() == b"Keep original bytes"


def test_source_size_limit_is_checked_before_read(tmp_path):
    source = tmp_path / "oversized.source"
    with source.open("wb") as file:
        file.truncate(15 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="byte limit"):
        read_source(source)


def test_prepare_uses_explicit_retrieval_time_instead_of_file_mtime(tmp_path):
    import os
    from datetime import UTC, datetime

    args = args_for(
        tmp_path, "kremlin", '<body><div itemprop="articleBody">Статья 1</div></body>'.encode()
    )
    args.retrieved_at = datetime(2026, 10, 28, 12, tzinfo=UTC)
    os.utime(args.source, (1, 1))
    prepare(args)
    manifest = SnapshotImport.model_validate_json(args.manifest.read_text())
    assert manifest.retrieved_at == args.retrieved_at


def test_prepare_rejects_naive_retrieval_time(tmp_path):
    from datetime import datetime

    args = args_for(
        tmp_path, "kremlin", '<body><div itemprop="articleBody">Статья 1</div></body>'.encode()
    )
    args.retrieved_at = datetime(2026, 10, 28)
    with pytest.raises(ValueError, match="timezone"):
        prepare(args)
    assert not args.manifest.exists()
