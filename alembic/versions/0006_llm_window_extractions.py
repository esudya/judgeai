"""Add the cache of LLM readings of short text windows.

Backfill: none. Downgrade drops only this cache; it is rebuilt by later analyses.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_llm_window_extractions"
down_revision = "0005_users"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "llm_window_extractions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("field", sa.String(80), nullable=False),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "input_hash", "field", "prompt_version", name="uq_llm_window_extraction"
        ),
    )


def downgrade():
    op.drop_table("llm_window_extractions")
