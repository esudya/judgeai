"""Legislation provenance, distinct from private cases and precedent decisions."""

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class LegalAct(Base):
    __tablename__ = "legal_acts"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('constitution','code','federal_law','plenum',"
            "'constitutional_court_decision')",
            name="ck_legal_acts_kind",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(40))
    number: Mapped[str | None] = mapped_column(String(80))
    adopted_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LegalEdition(Base):
    __tablename__ = "legal_editions"
    __table_args__ = (
        UniqueConstraint("act_id", "source_sha256", name="uq_legal_edition_snapshot"),
        CheckConstraint(
            "verification_status IN ('unreviewed','verified','rejected')",
            name="ck_legal_edition_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    act_id: Mapped[int] = mapped_column(
        ForeignKey("legal_acts.id", ondelete="RESTRICT"), index=True
    )
    label: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    source_sha256: Mapped[str] = mapped_column(String(64))
    source_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    full_text: Mapped[str] = mapped_column(Text)
    parser_version: Mapped[str] = mapped_column(String(120))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(20), server_default="unreviewed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LegalProvision(Base):
    __tablename__ = "legal_provisions"
    __table_args__ = (
        UniqueConstraint("edition_id", "locator", name="uq_legal_provision_locator"),
        UniqueConstraint("edition_id", "ordinal", name="uq_legal_provision_order"),
        CheckConstraint("ordinal >= 0", name="ck_legal_provision_order"),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name="ck_legal_provision_period",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    edition_id: Mapped[int] = mapped_column(
        ForeignKey("legal_editions.id", ondelete="RESTRICT"), index=True
    )
    locator: Mapped[str] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer)
    start_page: Mapped[int | None] = mapped_column(Integer)
    end_page: Mapped[int | None] = mapped_column(Integer)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class LegalRuleReference(Base):
    __tablename__ = "legal_rule_references"
    __table_args__ = (UniqueConstraint("rule_key", "provision_id", name="uq_legal_rule_reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_key: Mapped[str] = mapped_column(String(160), index=True)
    provision_id: Mapped[int] = mapped_column(
        ForeignKey("legal_provisions.id", ondelete="RESTRICT"), index=True
    )
    rationale: Mapped[str] = mapped_column(Text)
