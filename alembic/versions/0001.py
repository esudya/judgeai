"""Initial schema.

Originally this revision called `Base.metadata.create_all()`, which binds the migration to
whatever the models look like *today*: any later model change would be created here as well
and future revisions would collide. It is now frozen as explicit DDL that is identical to the
schema the old revision produced at commit 3f1994a, so databases already at 0001 stay valid.
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from src.config import settings

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    op.create_table(
        "chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "knowledge_verdicts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uid", sa.String(length=64), nullable=True),
        sa.Column("case_number", sa.String(length=64), nullable=True),
        sa.Column("court_name", sa.Text(), nullable=True),
        sa.Column("verdict_date", sa.Date(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_filename", sa.String(length=512), nullable=True),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("structured", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("uid"),
    )
    op.create_index("ix_knowledge_verdicts_file_hash", "knowledge_verdicts", ["file_hash"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_chat_id", "messages", ["chat_id"])

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "verdict_id", sa.Integer(),
            sa.ForeignKey("knowledge_verdicts.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("chunk_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        # Dimension follows settings, exactly like the model (and the old create_all) did.
        sa.Column("embedding", Vector(settings.EMBEDDING_DIM), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_verdict_id", "knowledge_chunks", ["verdict_id"])

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "message_id", sa.Integer(),
            sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("stored_path", sa.String(length=1024), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_attachments_message_id", "attachments", ["message_id"])


def downgrade() -> None:
    op.drop_table("attachments")
    op.drop_table("knowledge_chunks")
    op.drop_table("messages")
    op.drop_table("knowledge_verdicts")
    op.drop_table("chats")
    op.execute(sa.text("DROP EXTENSION IF EXISTS vector"))
