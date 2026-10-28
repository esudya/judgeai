"""Add vectors of anonymised fabulas for precedent search (T26).

Backfill: none; vectors are computed by `python -m src.cli.precedents index`. Downgrade drops
only the vectors; they are recomputed from precedent_cards.fabula.
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from src.config import settings

revision = "0008_precedent_embeddings"
down_revision = "0007_precedent_cards"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "precedent_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("embedding", Vector(settings.EMBEDDING_DIM)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("text_hash", "model", name="uq_precedent_embedding"),
    )


def downgrade():
    op.drop_table("precedent_embeddings")
