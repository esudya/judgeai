import hashlib
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import KnowledgeChunk, KnowledgeVerdict
from src.services.embeddings import embed_passages


def calculate_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def extract_basic_metadata(raw_text: str) -> dict:
    case_number = None
    court_name = None

    case_match = re.search(
        r"(?:дело|Дело)\s*№?\s*([0-9A-Za-zА-Яа-я\-_/]+)",
        raw_text,
    )

    if case_match:
        case_number = case_match.group(1)

    court_match = re.search(
        r"([А-Яа-яЁё\.\-\ ]+(?:районный|городской|областной|краевой).*?суд)",
        raw_text,
    )

    if court_match:
        court_name = court_match.group(1).strip()

    return {
        "case_number": case_number,
        "court_name": court_name,
    }


def build_chunks(raw_text: str) -> list[str]:
    text = raw_text.strip()

    if not text:
        return []

    paragraphs = [
        paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()
    ]

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 > settings.EMBEDDING_CHUNK_SIZE and current:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n{paragraph}" if current else paragraph

        if len(chunks) >= settings.EMBEDDING_MAX_CHUNKS:
            break

    if current and len(chunks) < settings.EMBEDDING_MAX_CHUNKS:
        chunks.append(current)

    if not chunks:
        chunks = [text[: settings.EMBEDDING_CHUNK_SIZE]]

    return [chunk[: settings.EMBEDDING_CHUNK_SIZE] for chunk in chunks]


async def create_knowledge_verdict_from_text(
    db: AsyncSession,
    filename: str,
    raw_text: str,
    source_type: str = "manual",
) -> tuple[KnowledgeVerdict, bool]:
    file_hash = calculate_text_hash(raw_text)

    existing = await db.scalar(
        select(KnowledgeVerdict).where(KnowledgeVerdict.file_hash == file_hash)
    )

    if existing:
        return existing, True

    metadata = extract_basic_metadata(raw_text)

    verdict = KnowledgeVerdict(
        case_number=metadata.get("case_number"),
        court_name=metadata.get("court_name"),
        source_type=source_type,
        source_filename=filename,
        file_hash=file_hash,
        raw_text=raw_text,
        structured=metadata,
        status="indexed",
    )

    db.add(verdict)
    await db.flush()

    chunks = build_chunks(raw_text)
    embeddings: list[list[float]] = []

    if chunks:
        try:
            embeddings = await embed_passages(chunks)
        except Exception:
            embeddings = []

    for index, chunk_text in enumerate(chunks):
        embedding = embeddings[index] if index < len(embeddings) else None

        db.add(
            KnowledgeChunk(
                verdict_id=verdict.id,
                chunk_type="text",
                content=chunk_text,
                embedding=embedding,
            )
        )

    if not chunks:
        verdict.status = "empty"
    elif not embeddings:
        verdict.status = "indexed_no_vectors"

    await db.flush()

    return verdict, False
