"""Import of structured sanctions from an imported edition and the read-only API."""

from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import func, select

from src.db.models import CriminalArticleSanction
from src.db.session import async_session_factory
from src.schemas.legal_library import SnapshotImport
from src.services.criminal_sanction_import import import_criminal_sanctions, latest_edition_id
from src.services.legal_library import import_snapshot

ARTICLE = (
    "Статья 158. Кража1. Кража -наказывается штрафом в размере до восьмидесяти тысяч рублей, "
    "либо лишением свободы на срок до двух лет.2. Кража, совершенная группой лиц, -наказывается "
    "лишением свободы на срок до пяти лет с ограничением свободы на срок до одного года или без "
    "такового."
)
NOTE = "Статья 159. Мошенничество без санкции в фикстуре."
RAW = b"synthetic fixture bytes for sanctions"


def _manifest() -> SnapshotImport:
    return SnapshotImport.model_validate(
        {
            "act": {"key": "uk-rf", "title": "УК РФ", "kind": "code", "number": "63-ФЗ"},
            "source_url": "https://pravo.gov.ru/test-fixture",
            "raw_sha256": sha256(RAW).hexdigest(),
            "retrieved_at": datetime(2026, 10, 28, tzinfo=UTC),
            "edition_label": "Synthetic edition",
            "full_text": ARTICLE + NOTE,
            "parser_version": "test-fixture-v1",
            "provisions": [
                {
                    "locator": "article.158",
                    "title": "Статья 158. Кража",
                    "body": ARTICLE,
                    "ordinal": 0,
                },
                {
                    "locator": "article.159",
                    "title": "Статья 159. Мошенничество",
                    "body": NOTE,
                    "ordinal": 1,
                },
                {"locator": "preamble", "title": "Преамбула", "body": "Статья 158.", "ordinal": 2},
            ],
        }
    )


async def _seed() -> int:
    async with async_session_factory() as db:
        edition, _ = await import_snapshot(db, _manifest(), RAW)
        await db.commit()
        return edition.id


async def test_import_is_idempotent_and_reports_counts():
    edition_id = await _seed()
    async with async_session_factory() as db:
        assert await latest_edition_id(db, "uk-rf") == edition_id
        first = await import_criminal_sanctions(db, edition_id)
        second = await import_criminal_sanctions(db, edition_id)
        total = await db.scalar(select(func.count()).select_from(CriminalArticleSanction))
    assert first == {"articles": 2, "articles_with_sanctions": 1, "sanctions": 4, "inserted": 4}
    assert second["inserted"] == 0
    assert total == 4


async def test_latest_edition_of_unknown_act_is_none():
    async with async_session_factory() as db:
        assert await latest_edition_id(db, "missing-act") is None


async def test_api_returns_part_sanctions_with_provenance(client):
    edition_id = await _seed()
    async with async_session_factory() as db:
        await import_criminal_sanctions(db, edition_id)

    response = await client.get("/api/legal/sanctions", params={"article": "158", "part": 2})
    assert response.status_code == 200
    body = response.json()
    assert [(s["kind"], s["role"], s["max_value"]) for s in body] == [
        ("imprisonment", "main", 60),
        ("restriction_of_freedom", "additional", 12),
    ]
    provenance = body[0]["provenance"]
    assert provenance["verification_status"] == "unreviewed"
    assert provenance["source_url"] == "https://pravo.gov.ru/test-fixture"
    assert provenance["provision_locator"] == "article.158"


async def test_api_unknown_article_is_404_and_bad_article_is_422(client):
    assert (await client.get("/api/legal/sanctions", params={"article": "158"})).status_code == 404
    assert (await client.get("/api/legal/sanctions", params={"article": "x;"})).status_code == 422


async def test_lookup_returns_domain_sanctions_of_one_part():
    from src.services.criminal_sanction_lookup import find_article_sanctions

    edition_id = await _seed()
    async with async_session_factory() as db:
        await import_criminal_sanctions(db, edition_id)
        reading = await find_article_sanctions(db, "158", 1)
        missing = await find_article_sanctions(db, "999")
    assert missing is None
    assert {(s.kind.value, s.max_value) for s in reading.sanctions} == {
        ("fine", 80_000),
        ("imprisonment", 24),
    }
    assert reading.provenance.edition_id == edition_id


async def test_cli_import_reports_edition_and_refuses_unknown_act():
    import pytest

    from src.cli.criminal_sanctions import run_import

    edition_id = await _seed()
    report = await run_import("uk-rf")
    assert report["edition_id"] == edition_id and report["inserted"] == 4
    with pytest.raises(SystemExit):
        await run_import("missing-act")
