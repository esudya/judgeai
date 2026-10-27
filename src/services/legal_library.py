"""Trusted local import; never marks a fetched text legally verified."""

from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import LegalAct, LegalEdition, LegalProvision
from src.schemas.legal_library import SnapshotImport

MAX_SOURCE_BYTES = 15 * 1024 * 1024


async def import_snapshot(
    db: AsyncSession,
    manifest: SnapshotImport,
    raw: bytes,
) -> tuple[LegalEdition, bool]:
    if not raw or len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("source byte size is outside the allowed range")
    if sha256(raw).hexdigest() != manifest.raw_sha256:
        raise ValueError("source hash mismatch")
    if any(not p.body.strip() or p.body not in manifest.full_text for p in manifest.provisions):
        raise ValueError("provision is missing from source text")
    act_data = manifest.act.model_dump()
    await db.execute(
        insert(LegalAct).values(**act_data).on_conflict_do_nothing(index_elements=["key"])
    )
    act = await db.scalar(select(LegalAct).where(LegalAct.key == manifest.act.key))
    if any(getattr(act, field) != value for field, value in act_data.items()):
        raise ValueError("act identity conflicts with existing metadata")
    edition_id = await db.scalar(
        insert(LegalEdition)
        .values(
            act_id=act.id,
            label=manifest.edition_label,
            source_url=manifest.source_url,
            source_sha256=manifest.raw_sha256,
            source_bytes=raw,
            full_text=manifest.full_text,
            parser_version=manifest.parser_version,
            retrieved_at=manifest.retrieved_at,
            verification_status="unreviewed",
        )
        .on_conflict_do_nothing(constraint="uq_legal_edition_snapshot")
        .returning(LegalEdition.id)
    )
    if edition_id is None:
        existing = await db.scalar(
            select(LegalEdition).where(
                LegalEdition.act_id == act.id, LegalEdition.source_sha256 == manifest.raw_sha256
            )
        )
        if existing.full_text != manifest.full_text:
            raise ValueError("same raw snapshot has different extracted text; preserve old import")
        stored = (
            await db.scalars(
                select(LegalProvision)
                .where(LegalProvision.edition_id == existing.id)
                .order_by(LegalProvision.ordinal)
            )
        ).all()
        fields = tuple(type(manifest.provisions[0]).model_fields)
        old_index = [{field: getattr(item, field) for field in fields} for item in stored]
        new_index = [
            item.model_dump() for item in sorted(manifest.provisions, key=lambda item: item.ordinal)
        ]
        if old_index != new_index or existing.parser_version != manifest.parser_version:
            raise ValueError("same raw snapshot has a different index; preserve old import")
        return existing, False
    db.add_all(
        [LegalProvision(edition_id=edition_id, **p.model_dump()) for p in manifest.provisions]
    )
    await db.flush()
    return await db.get(LegalEdition, edition_id), True
