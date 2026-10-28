"""Add precedent cards and the registry of their extracted fields (T24/T25).

Backfill: none; cards are built from knowledge_verdicts by
`python -m src.cli.precedents index`. Downgrade drops only these derived tables; verdicts in
knowledge_verdicts and all case data stay untouched and cards can be rebuilt.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_precedent_cards"
down_revision = "0006_llm_window_extractions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "precedent_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "knowledge_verdict_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_verdicts.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("text_sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("uid", sa.String(64)),
        sa.Column("court_name", sa.Text()),
        sa.Column("decision_date", sa.Date()),
        sa.Column("source_url", sa.Text()),
        sa.Column("main_article", sa.String(16)),
        sa.Column("main_part", sa.Integer()),
        sa.Column("qualification_keys", postgresql.ARRAY(sa.String(32)), nullable=False),
        sa.Column("mitigating", postgresql.ARRAY(sa.String(16)), nullable=False),
        sa.Column("aggravating", postgresql.ARRAY(sa.String(16)), nullable=False),
        sa.Column("applied_general", postgresql.ARRAY(sa.String(8)), nullable=False),
        sa.Column("recidivism", sa.String(32)),
        sa.Column("conditional", sa.Boolean(), nullable=False),
        sa.Column("imprisonment_months", sa.Integer()),
        sa.Column("episodes", postgresql.JSONB(), nullable=False),
        sa.Column("final", postgresql.JSONB()),
        sa.Column("fabula", sa.Text(), nullable=False),
        sa.Column("embedding_text_hash", sa.String(64)),
        sa.Column("extractor_version", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_precedent_cards_uid", "precedent_cards", ["uid"])
    op.create_index(
        "ix_precedent_cards_embedding_text_hash", "precedent_cards", ["embedding_text_hash"]
    )
    op.create_index("ix_precedent_cards_main", "precedent_cards", ["main_article", "main_part"])
    op.create_index(
        "ix_precedent_cards_qualifications",
        "precedent_cards",
        ["qualification_keys"],
        postgresql_using="gin",
    )
    op.execute(
        "CREATE INDEX ix_precedent_cards_fabula_tsv ON precedent_cards "
        "USING gin (to_tsvector('russian', fabula))"
    )
    op.create_table(
        "precedent_card_fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "card_id",
            sa.Integer(),
            sa.ForeignKey("precedent_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("value", postgresql.JSONB()),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("extractor_version", sa.String(64), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "card_id", "name", "extractor_version", "input_hash", name="uq_precedent_card_field"
        ),
    )
    op.create_index("ix_precedent_card_fields_card_id", "precedent_card_fields", ["card_id"])


def downgrade():
    op.drop_table("precedent_card_fields")
    op.drop_table("precedent_cards")
