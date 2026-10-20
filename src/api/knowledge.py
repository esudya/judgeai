from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy import func, or_, select

from src.api.deps import DbSession
from src.db.models import KnowledgeChunk, KnowledgeVerdict
from src.schemas.knowledge import (
    KnowledgeListResponse,
    KnowledgeUploadItem,
    KnowledgeUploadResponse,
    KnowledgeVerdictDetail,
    KnowledgeVerdictRead,
)
from src.services.document_parser import extract_text_from_file
from src.services.file_reader import save_upload_file
from src.services.knowledge_service import create_knowledge_verdict_from_text

router = APIRouter()


@router.post("/verdicts/upload", response_model=KnowledgeUploadResponse)
async def upload_verdicts(
    db: DbSession,
    files: list[UploadFile] = File(default_factory=list),
    source_type: str = Form("manual"),
):
    if not files:
        raise HTTPException(status_code=422, detail="Не переданы файлы")

    items: list[KnowledgeUploadItem] = []

    for file in files:
        stored_path, _ = await save_upload_file(file)
        raw_text = await extract_text_from_file(stored_path)

        verdict, duplicate = await create_knowledge_verdict_from_text(
            db=db,
            filename=file.filename or "file",
            raw_text=raw_text,
            source_type=source_type,
        )

        items.append(
            KnowledgeUploadItem(
                verdict_id=verdict.id,
                filename=file.filename or "file",
                status=verdict.status,
                duplicate=duplicate,
                case_number=verdict.case_number,
                court_name=verdict.court_name,
                verdict_date=verdict.verdict_date,
                warnings=[],
            )
        )

    await db.commit()

    return KnowledgeUploadResponse(uploaded=len(items), items=items)


@router.get("/verdicts", response_model=KnowledgeListResponse)
async def list_verdicts(
    db: DbSession,
    page: int = 1,
    size: int = 20,
    q: str | None = None,
):
    base_stmt = select(KnowledgeVerdict)
    count_stmt = select(func.count(KnowledgeVerdict.id))

    if q:
        filter_expr = or_(
            KnowledgeVerdict.case_number.ilike(f"%{q}%"),
            KnowledgeVerdict.court_name.ilike(f"%{q}%"),
            KnowledgeVerdict.source_filename.ilike(f"%{q}%"),
        )

        base_stmt = base_stmt.where(filter_expr)
        count_stmt = count_stmt.where(filter_expr)

    total = await db.scalar(count_stmt)

    stmt = (
        base_stmt
        .order_by(KnowledgeVerdict.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )

    result = await db.scalars(stmt)
    items = [KnowledgeVerdictRead.model_validate(verdict) for verdict in result.all()]

    return KnowledgeListResponse(
        total=total or 0,
        page=page,
        size=size,
        items=items,
    )


@router.get("/verdicts/{verdict_id}", response_model=KnowledgeVerdictDetail)
async def get_verdict(verdict_id: int, db: DbSession):
    verdict = await db.get(KnowledgeVerdict, verdict_id)

    if not verdict:
        raise HTTPException(status_code=404, detail="Приговор не найден")

    chunks_count = await db.scalar(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.verdict_id == verdict_id
        )
    )

    return KnowledgeVerdictDetail(
        id=verdict.id,
        uid=verdict.uid,
        case_number=verdict.case_number,
        court_name=verdict.court_name,
        verdict_date=verdict.verdict_date,
        source_type=verdict.source_type,
        source_filename=verdict.source_filename,
        file_hash=verdict.file_hash,
        status=verdict.status,
        created_at=verdict.created_at,
        structured=verdict.structured,
        chunks_count=chunks_count or 0,
    )


@router.delete("/verdicts/{verdict_id}")
async def delete_verdict(verdict_id: int, db: DbSession):
    verdict = await db.get(KnowledgeVerdict, verdict_id)

    if not verdict:
        raise HTTPException(status_code=404, detail="Приговор не найден")

    await db.delete(verdict)
    await db.commit()

    return {"ok": True}
