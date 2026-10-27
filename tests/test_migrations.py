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
