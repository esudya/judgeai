"""Add structured УК РФ sanctions derived from imported legal editions.

Backfill: none (filled by `python -m src.cli.criminal_sanctions import`). Downgrade drops
only this derived table; it can be rebuilt from legal_provisions at any time.
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_criminal_article_sanctions"
down_revision = "0003_legal_library"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "criminal_article_sanctions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "provision_id",
            sa.Integer(),
            sa.ForeignKey("legal_provisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("article", sa.String(20), nullable=False),
        sa.Column("part", sa.Integer()),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("min_value", sa.Float()),
        sa.Column("max_value", sa.Float()),
        sa.Column("unit", sa.String(20)),
        sa.Column("clause", sa.Text(), nullable=False),
        sa.Column("parser_version", sa.String(80), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "provision_id", "parser_version", "ordinal", name="uq_criminal_sanction_reading"
        ),
        sa.CheckConstraint("role IN ('main','additional')", name="ck_criminal_sanction_role"),
        sa.CheckConstraint(
            "min_value IS NULL OR max_value IS NULL OR min_value <= max_value",
            name="ck_criminal_sanction_bounds",
        ),
    )
    op.create_index(
        "ix_criminal_article_sanctions_provision_id", "criminal_article_sanctions", ["provision_id"]
    )
    op.create_index(
        "ix_criminal_article_sanctions_article", "criminal_article_sanctions", ["article"]
    )


def downgrade():
    op.drop_table("criminal_article_sanctions")
