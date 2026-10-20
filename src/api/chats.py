from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import DbSession
from src.db.models import Attachment, Chat, Message
from src.schemas.chat import ChatCreate, ChatRead
from src.schemas.message import MessageRead, MessageSendResponse
from src.services.case_analyzer import analyze_case
from src.services.document_parser import extract_text_from_file
from src.services.file_reader import save_upload_file
from src.services.knowledge_service import create_knowledge_verdict_from_text
from src.services.similarity_search import find_similar_verdicts

router = APIRouter()


async def load_message(db: AsyncSession, message_id: int) -> Message:
    stmt = (
        select(Message)
        .options(selectinload(Message.attachments))
        .where(Message.id == message_id)
    )
    message = await db.scalar(stmt)

    if not message:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")

    return message


@router.get("", response_model=list[ChatRead])
async def list_chats(db: DbSession):
    stmt = select(Chat).order_by(Chat.updated_at.desc())
    result = await db.scalars(stmt)
    return [ChatRead.model_validate(chat) for chat in result.all()]


@router.post("", response_model=ChatRead, status_code=201)
async def create_chat(payload: ChatCreate, db: DbSession):
    chat = Chat(title=payload.title)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return ChatRead.model_validate(chat)


@router.get("/{chat_id}", response_model=ChatRead)
async def get_chat(chat_id: int, db: DbSession):
    chat = await db.get(Chat, chat_id)

    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    return ChatRead.model_validate(chat)


@router.get("/{chat_id}/messages", response_model=list[MessageRead])
async def list_messages(chat_id: int, db: DbSession):
    chat = await db.get(Chat, chat_id)

    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    stmt = (
        select(Message)
        .options(selectinload(Message.attachments))
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at)
    )

    result = await db.scalars(stmt)
    return [MessageRead.model_validate(message) for message in result.all()]


@router.post("/{chat_id}/messages", response_model=MessageSendResponse)
async def create_message(
    chat_id: int,
    db: DbSession,
    content: str | None = Form(None),
    use_knowledge_base: bool = Form(True),
    save_to_knowledge_base: bool = Form(False),
    files: list[UploadFile] = File(default_factory=list),
):
    chat = await db.get(Chat, chat_id)

    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    user_message = Message(
        chat_id=chat_id,
        role="user",
        content=content,
        status="completed",
    )

    db.add(user_message)
    await db.flush()

    document_texts: list[str] = []

    for file in files:
        stored_path, size = await save_upload_file(file)
        extracted_text = await extract_text_from_file(stored_path)

        attachment = Attachment(
            message_id=user_message.id,
            filename=file.filename or "file",
            content_type=file.content_type,
            size=size,
            stored_path=str(stored_path),
            extracted_text=extracted_text,
        )

        db.add(attachment)
        document_texts.append(extracted_text)

        if save_to_knowledge_base:
            await create_knowledge_verdict_from_text(
                db=db,
                filename=file.filename or "file",
                raw_text=extracted_text,
                source_type="chat",
            )

    await db.commit()

    similar_items: list[dict] = []

    if use_knowledge_base:
        similar_items = await find_similar_verdicts(
            db=db,
            query_text=content or "",
            document_texts=document_texts,
        )

    assistant_content, analysis = await analyze_case(
        question=content,
        document_texts=document_texts,
        similar_items=similar_items,
    )

    assistant_message = Message(
        chat_id=chat_id,
        role="assistant",
        content=assistant_content,
        status="completed",
        analysis=analysis,
    )

    db.add(assistant_message)
    await db.commit()

    user_message_loaded = await load_message(db, user_message.id)
    assistant_message_loaded = await load_message(db, assistant_message.id)

    return MessageSendResponse(
        user_message=MessageRead.model_validate(user_message_loaded),
        assistant_message=MessageRead.model_validate(assistant_message_loaded),
    )
