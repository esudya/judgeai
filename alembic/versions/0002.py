"""Analysis progress and attachment extraction metadata.

Additive and reversible; no data is rewritten:
  messages.stage              nullable    current analysis stage while status = running
  messages.updated_at         NOT NULL    server default now() (fills existing rows)
  attachments.page_count      nullable    known for PDF, unknown for other formats
  attachments.extraction_status NOT NULL  server default 'ok' (existing rows were treated as ok)
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("stage", sa.String(length=32), nullable=True))
    op.add_column(
        "messages",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("attachments", sa.Column("page_count", sa.Integer(), nullable=True))
    op.add_column(
        "attachments",
        sa.Column("extraction_status", sa.String(length=16), server_default="ok", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("attachments", "extraction_status")
    op.drop_column("attachments", "page_count")
    op.drop_column("messages", "updated_at")
    op.drop_column("messages", "stage")
