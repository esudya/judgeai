from datetime import UTC, date, datetime
from hashlib import sha256

import pytest
from sqlalchemy import func, select

from src.db.models import LegalAct, LegalEdition, LegalProvision
from src.db.session import async_session_factory
from src.schemas.legal_library import SnapshotImport
from src.services.legal_library import import_snapshot

RAW = b"Synthetic official-source fixture, not a real law"


def manifest(**updates):
    data = {
        "act": {
            "key": "synthetic-act",
            "title": "Synthetic act",
            "kind": "code",
            "number": "1",
            "adopted_on": "2020-01-01",
        },
        "source_url": "https://pravo.gov.ru/test-fixture",
        "raw_sha256": sha256(RAW).hexdigest(),
        "retrieved_at": datetime(2026, 10, 27, tzinfo=UTC),
        "edition_label": "Synthetic edition",
        "full_text": "Article 1. Synthetic rule. Article 2. Another rule.",
        "parser_version": "test-fixture-v1",
        "provisions": [
            {
                "locator": "article.1",
                "title": "Article 1",
                "body": "Article 1. Synthetic rule.",
                "ordinal": 0,
            }
        ],
    }
    data.update(updates)
    return SnapshotImport.model_validate(data)


async def test_import_preserves_source_and_is_idempotent():
    async with async_session_factory() as db:
        first, created = await import_snapshot(db, manifest(), RAW)
        assert created
        await db.commit()
        repeated, created = await import_snapshot(db, manifest(), RAW)
        await db.commit()
        assert not created and repeated.id == first.id
        assert first.source_bytes == RAW
        assert first.verification_status == "unreviewed"
        assert first.source_url == "https://pravo.gov.ru/test-fixture"
        assert await db.scalar(select(func.count()).select_from(LegalAct)) == 1
        assert await db.scalar(select(func.count()).select_from(LegalEdition)) == 1
        assert await db.scalar(select(func.count()).select_from(LegalProvision)) == 1


async def test_bad_hash_is_rejected_without_partial_writes():
    async with async_session_factory() as db:
        with pytest.raises(ValueError, match="hash"):
            await import_snapshot(db, manifest(), b"changed bytes")
        assert await db.scalar(select(func.count()).select_from(LegalAct)) == 0


def test_untrusted_host_and_empty_text_are_rejected():
    with pytest.raises(ValueError):
        manifest(source_url="https://pravo.gov.ru.evil.example/act")
    with pytest.raises(ValueError):
        manifest(full_text=" ")


async def test_fabricated_provision_is_rejected():
    data = manifest().model_dump()
    data["provisions"][0]["body"] = "A fabricated rule missing from source"
    async with async_session_factory() as db:
        with pytest.raises(ValueError, match="source text"):
            await import_snapshot(db, SnapshotImport.model_validate(data), RAW)
        assert await db.scalar(select(func.count()).select_from(LegalAct)) == 0


async def test_read_only_catalogue_and_unreviewed_lookup(client):
    async with async_session_factory() as db:
        edition, _ = await import_snapshot(db, manifest(), RAW)
        await db.commit()
    acts = (await client.get("/api/legal/acts")).json()
    assert acts["total"] == 1 and acts["items"][0]["key"] == "synthetic-act"
    response = await client.get(
        f"/api/legal/editions/{edition.id}/provisions", params={"q": "Synthetic"}
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["locator"] == "article.1"
    assert response.json()["verification_status"] == "unreviewed"
    response = await client.get(
        "/api/legal/lookup",
        params={"act": "synthetic-act", "locator": "article.1", "on": "2026-10-27"},
    )
    assert response.status_code == 404
    assert (await client.post("/api/legal/acts", json={})).status_code == 405


async def test_date_lookup_excludes_unknown_dates_and_uses_half_open_interval(client):
    async with async_session_factory() as db:
        edition, _ = await import_snapshot(db, manifest(), RAW)
        edition.verification_status = "verified"
        provision = await db.scalar(select(LegalProvision))
        provision.effective_from = date(2020, 1, 1)
        provision.effective_to = date(2026, 1, 1)
        await db.commit()
    params = {"act": "synthetic-act", "locator": "article.1", "on": "2025-12-31"}
    response = await client.get("/api/legal/lookup", params=params)
    assert response.status_code == 200
    assert response.json()["source_sha256"] == sha256(RAW).hexdigest()
    params["on"] = "2026-01-01"
    assert (await client.get("/api/legal/lookup", params=params)).status_code == 404
    async with async_session_factory() as db:
        provision = await db.scalar(select(LegalProvision))
        provision.effective_from = None
        provision.effective_to = None
        await db.commit()
    assert (await client.get("/api/legal/lookup", params=params)).status_code == 404


async def test_conflicting_verified_editions_fail_closed(client):
    async with async_session_factory() as db:
        first, _ = await import_snapshot(db, manifest(), RAW)
        other_raw = RAW + b"2"
        second, _ = await import_snapshot(
            db, manifest(raw_sha256=sha256(other_raw).hexdigest()), other_raw
        )
        first.verification_status = second.verification_status = "verified"
        for item in (await db.scalars(select(LegalProvision))).all():
            item.effective_from = date(2020, 1, 1)
        await db.commit()
    response = await client.get(
        "/api/legal/lookup",
        params={"act": "synthetic-act", "locator": "article.1", "on": "2026-10-27"},
    )
    assert response.status_code == 409


async def test_api_pagination_is_bounded(client):
    assert (await client.get("/api/legal/acts", params={"size": 1001})).status_code == 422
    assert (await client.get("/api/legal/acts", params={"page": 0})).status_code == 422


async def test_same_snapshot_cannot_silently_change_its_index():
    async with async_session_factory() as db:
        await import_snapshot(db, manifest(), RAW)
        await db.commit()
        data = manifest().model_dump()
        data["provisions"][0]["locator"] = "article.changed"
        with pytest.raises(ValueError, match="index"):
            await import_snapshot(db, SnapshotImport.model_validate(data), RAW)


async def test_concurrent_imports_share_one_snapshot():
    import asyncio

    async def run():
        async with async_session_factory() as db, db.begin():
            edition, created = await import_snapshot(db, manifest(), RAW)
            return edition.id, created

    results = await asyncio.gather(run(), run())
    assert results[0][0] == results[1][0]
    assert sum(created for _, created in results) == 1


async def test_metadata_requests_do_not_load_source_payloads(client):
    from sqlalchemy import event

    from src.db.session import engine

    async with async_session_factory() as db:
        edition, _ = await import_snapshot(db, manifest(), RAW)
        edition.verification_status = "verified"
        provision = await db.scalar(select(LegalProvision))
        provision.effective_from = date(2020, 1, 1)
        await db.commit()
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        for url in (
            "/api/legal/acts/synthetic-act/editions",
            f"/api/legal/editions/{edition.id}/provisions",
            "/api/legal/lookup?act=synthetic-act&locator=article.1&on=2026-10-28",
        ):
            assert (await client.get(url)).status_code == 200
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    edition_queries = [s for s in statements if "legal_editions" in s and "SELECT" in s]
    assert len(edition_queries) >= 3
    assert all("legal_editions.source_bytes" not in s for s in edition_queries)
    assert all("legal_editions.full_text" not in s for s in edition_queries)
