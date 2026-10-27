from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from src.db import models  # noqa: F401  (registers tables on Base.metadata)
from src.db.base import Base
from tests.conftest import alembic_config


async def test_migrations_match_models():
    """`alembic upgrade head` must produce exactly the schema the models describe."""
    from src.db.session import engine

    async with engine.connect() as conn:
        diff = await conn.run_sync(
            lambda sync_conn: compare_metadata(MigrationContext.configure(sync_conn), Base.metadata)
        )
    assert diff == []


def test_downgrade_and_upgrade_roundtrip():
    cfg = alembic_config()
    command.downgrade(cfg, "0001")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


def test_legal_library_downgrade_keeps_existing_case_data():
    import asyncio

    from src.db.models import Chat
    from src.db.session import async_session_factory

    async def create_case():
        async with async_session_factory() as db:
            chat = Chat(title="Case survives legal-library rollback")
            db.add(chat)
            await db.commit()
            return chat.id

    async def read_case(chat_id):
        async with async_session_factory() as db:
            return (await db.get(Chat, chat_id)).title

    chat_id = asyncio.run(create_case())
    cfg = alembic_config()
    command.downgrade(cfg, "0002")
    try:
        assert asyncio.run(read_case(chat_id)) == "Case survives legal-library rollback"
    finally:
        command.upgrade(cfg, "head")
    assert asyncio.run(read_case(chat_id)) == "Case survives legal-library rollback"
