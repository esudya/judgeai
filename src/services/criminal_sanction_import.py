"""Use case: derive structured sanctions from the provisions of an imported УК РФ edition.

Idempotent per (provision, parser version): a repeated run adds nothing. A new parser
version adds a new reading next to the old one instead of overwriting it.
"""

import re

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import CriminalArticleSanction, LegalAct, LegalEdition, LegalProvision
from src.services.statute_sanction_parser import PARSER_VERSION, parse_article_sanctions

_ARTICLE_LOCATOR = re.compile(r"^article\.(\d+(?:\.\d+)*)$")


async def import_criminal_sanctions(db: AsyncSession, edition_id: int) -> dict[str, int]:
    """Parse every article of the edition; returns counters for the import report."""
    provisions = (
        await db.scalars(
            select(LegalProvision)
            .where(LegalProvision.edition_id == edition_id)
            .order_by(LegalProvision.ordinal)
        )
    ).all()
    report = {"articles": 0, "articles_with_sanctions": 0, "sanctions": 0, "inserted": 0}
    for provision in provisions:
        locator = _ARTICLE_LOCATOR.match(provision.locator)
        if not locator:
            continue
        report["articles"] += 1
        sanctions = parse_article_sanctions(locator[1], provision.body, provision.title)
        if sanctions:
            report["articles_with_sanctions"] += 1
        report["sanctions"] += len(sanctions)
        for ordinal, sanction in enumerate(sanctions):
            result = await db.execute(
                insert(CriminalArticleSanction)
                .values(
                    provision_id=provision.id,
                    article=sanction.article,
                    part=sanction.part,
                    ordinal=ordinal,
                    kind=sanction.kind.value,
                    role=sanction.role.value,
                    min_value=sanction.min_value,
                    max_value=sanction.max_value,
                    unit=sanction.unit.value if sanction.unit else None,
                    clause=sanction.clause,
                    parser_version=PARSER_VERSION,
                )
                .on_conflict_do_nothing(constraint="uq_criminal_sanction_reading")
            )
            report["inserted"] += result.rowcount or 0
    await db.commit()
    return report


async def latest_edition_id(db: AsyncSession, act_key: str) -> int | None:
    return await db.scalar(
        select(LegalEdition.id)
        .join(LegalAct, LegalAct.id == LegalEdition.act_id)
        .where(LegalAct.key == act_key)
        .order_by(LegalEdition.retrieved_at.desc(), LegalEdition.id.desc())
        .limit(1)
    )
