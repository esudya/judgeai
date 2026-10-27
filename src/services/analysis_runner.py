"""Background execution of a case analysis.

The request handler stores the files and returns immediately with an assistant message in
status "pending"; this runner then walks the stages and updates the message so the UI can poll:
    reading -> searching -> qualifying -> checking -> completed | failed
(similar verdicts are searched before the LLM call because they are part of its prompt)
"""

import logging
import time
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from src.db import session as db_session
from src.db.models import Chat, Message
from src.services.case_analyzer import assemble_analysis, extract_facts
from src.services.document_parser import extract_document
from src.services.knowledge_service import create_knowledge_verdict_from_text
from src.services.llm_client import LLMError, get_llm_client
from src.services.similarity_search import find_similar_verdicts

logger = logging.getLogger(__name__)

INTERRUPTED_ERROR = "Анализ прерван перезапуском сервера"


async def _set_stage(message_id: int, *, status: str = "running", stage: str | None = None) -> None:
    async with db_session.async_session_factory() as db:
        await db.execute(
            update(Message).where(Message.id == message_id).values(status=status, stage=stage)
        )
        await db.commit()


async def run_analysis(
    user_message_id: int,
    assistant_message_id: int,
    *,
    save_to_knowledge_base: bool = False,
    use_knowledge_base: bool = True,
) -> None:
    started = time.monotonic()
    try:
        await _set_stage(assistant_message_id, stage="reading")
        async with db_session.async_session_factory() as db:
            user_message = await db.scalar(
                select(Message)
                .options(selectinload(Message.attachments))
                .where(Message.id == user_message_id)
            )
            if user_message is None:
                raise RuntimeError("user message disappeared")

            texts: list[str] = []
            pages = 0
            warnings: list[str] = []
            for att in user_message.attachments:
                doc = await extract_document(Path(att.stored_path))
                att.extracted_text = doc.text
                att.page_count = doc.page_count
                att.extraction_status = doc.status
                texts.append(doc.text)
                pages += doc.page_count or 0
                if doc.status in ("partial", "empty", "error"):
                    warnings.append(f"«{att.filename}»: текст распознан {_status_ru(doc.status)}.")
                if save_to_knowledge_base and doc.text.strip():
                    await create_knowledge_verdict_from_text(
                        db=db, filename=att.filename, raw_text=doc.text, source_type="chat"
                    )
            question = user_message.content
            chat_id = user_message.chat_id
            documents = len(user_message.attachments)
            await db.commit()

        await _set_stage(assistant_message_id, stage="searching")
        similar_items: list[dict] = []
        if use_knowledge_base:
            async with db_session.async_session_factory() as db:
                similar_items = await find_similar_verdicts(
                    db=db, query_text=question or "", document_texts=texts
                )

        await _set_stage(assistant_message_id, stage="qualifying")
        facts = await extract_facts(get_llm_client(), question, texts, similar_items)

        await _set_stage(assistant_message_id, stage="checking")
        analysis = assemble_analysis(
            facts,
            prompt=question or "",
            documents=documents,
            pages=pages,
            seconds=round(time.monotonic() - started),
            similar_items=similar_items,
            extra_warnings=warnings,
        )

        async with db_session.async_session_factory() as db:
            await db.execute(
                update(Message)
                .where(Message.id == assistant_message_id)
                .values(
                    status="completed",
                    stage=None,
                    content=analysis.fabula,
                    analysis=analysis.model_dump(mode="json"),
                    error=None,
                )
            )
            # Untitled cases get their qualification as a title (the sidebar shows it).
            if analysis.qualification:
                await db.execute(
                    update(Chat)
                    .where(Chat.id == chat_id, Chat.title.is_(None))
                    .values(title=analysis.qualification.article[:255])
                )
            await db.commit()
    except Exception as exc:
        logger.exception("analysis failed for message %s", assistant_message_id)
        # LLMError messages are written for users; anything else is an internal error.
        error = str(exc) if isinstance(exc, LLMError) else "Внутренняя ошибка анализа"
        async with db_session.async_session_factory() as db:
            await db.execute(
                update(Message)
                .where(Message.id == assistant_message_id)
                .values(status="failed", stage=None, error=error)
            )
            await db.commit()


def _status_ru(status: str) -> str:
    return {
        "partial": "частично",
        "empty": "пустым — нет текстового слоя",
        "error": "с ошибкой",
    }.get(status, status)


async def fail_interrupted_analyses() -> int:
    """BackgroundTasks die with the process: mark leftovers as failed on startup."""
    async with db_session.async_session_factory() as db:
        result = await db.execute(
            update(Message)
            .where(Message.status.in_(("pending", "running")), Message.role == "assistant")
            .values(status="failed", stage=None, error=INTERRUPTED_ERROR)
        )
        await db.commit()
        return result.rowcount or 0
