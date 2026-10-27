"""Structured sanctions of УК РФ articles, derived from an imported legal edition.

Each row keeps its provenance: the exact provision (and through it the edition, URL and
SHA-256) and the parser version. Review status is inherited from the edition.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class CriminalArticleSanction(Base):
    __tablename__ = "criminal_article_sanctions"
    __table_args__ = (
        UniqueConstraint(
            "provision_id", "parser_version", "ordinal", name="uq_criminal_sanction_reading"
        ),
        CheckConstraint("role IN ('main','additional')", name="ck_criminal_sanction_role"),
        CheckConstraint(
            "min_value IS NULL OR max_value IS NULL OR min_value <= max_value",
            name="ck_criminal_sanction_bounds",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provision_id: Mapped[int] = mapped_column(
        ForeignKey("legal_provisions.id", ondelete="RESTRICT"), index=True
    )
    article: Mapped[str] = mapped_column(String(20), index=True)
    part: Mapped[int | None] = mapped_column(Integer)
    ordinal: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    role: Mapped[str] = mapped_column(String(20))
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(20))
    clause: Mapped[str] = mapped_column(Text)
    parser_version: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
