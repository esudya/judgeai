from alembic import op
from sqlalchemy import text

from src.db.base import Base
from src.db import models

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

    op.execute(text("DROP EXTENSION IF EXISTS vector"))
