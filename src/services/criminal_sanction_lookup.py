"""Query: structured sanctions of an article from the newest parsed edition, with provenance."""

from dataclasses import dataclass

from legal_core.entities import MeasureUnit, PunishmentKind, SanctionRole, StatutorySanction
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import CriminalArticleSanction, LegalEdition, LegalProvision
from src.schemas.criminal_sanctions import SanctionProvenance


@dataclass(frozen=True)
class StatuteSanctionReading:
    sanctions: list[StatutorySanction]
    provenance: SanctionProvenance


async def find_article_sanctions(
    db: AsyncSession, article: str, part: int | None = None
) -> StatuteSanctionReading | None:
    query = (
        select(CriminalArticleSanction, LegalProvision, LegalEdition)
        .join(LegalProvision, LegalProvision.id == CriminalArticleSanction.provision_id)
        .join(LegalEdition, LegalEdition.id == LegalProvision.edition_id)
        .where(CriminalArticleSanction.article == article)
        .order_by(
            LegalEdition.retrieved_at.desc(),
            CriminalArticleSanction.parser_version.desc(),
            CriminalArticleSanction.ordinal,
        )
    )
    if part is not None:
        query = query.where(CriminalArticleSanction.part == part)
    rows = (await db.execute(query)).all()
    if not rows:
        return None
    _, provision, edition = rows[0]
    newest_version = rows[0][0].parser_version
    sanctions = [
        StatutorySanction(
            article=row.article,
            part=row.part,
            kind=PunishmentKind(row.kind),
            role=SanctionRole(row.role),
            min_value=row.min_value,
            max_value=row.max_value,
            unit=MeasureUnit(row.unit) if row.unit else None,
            clause=row.clause,
        )
        for row, _, row_edition in rows
        if row_edition.id == edition.id and row.parser_version == newest_version
    ]
    provenance = SanctionProvenance(
        edition_id=edition.id,
        edition_label=edition.label,
        source_url=edition.source_url,
        source_sha256=edition.source_sha256,
        verification_status=edition.verification_status,
        provision_locator=provision.locator,
        parser_version=newest_version,
    )
    return StatuteSanctionReading(sanctions=sanctions, provenance=provenance)
