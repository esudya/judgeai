# Domain Layer — value objects used by the rules.
from dataclasses import dataclass
from enum import Enum


class Guilt(str, Enum):
    INTENTIONAL = "intentional"
    NEGLIGENT = "negligent"


class Category(int, Enum):
    """Crime categories of art. 15; the value orders them by gravity."""

    SMALL = 1
    MEDIUM = 2
    GRAVE = 3
    ESPECIALLY_GRAVE = 4


@dataclass(frozen=True)
class SanctionCeiling:
    """Upper bound of the article's sanction (comes from the DB, never hardcoded).

    max_imprisonment_months is None when the sanction has no imprisonment at all.
    harsher_than_imprisonment marks life imprisonment / death penalty in the sanction.
    """

    max_imprisonment_months: int | None
    harsher_than_imprisonment: bool = False

    def __post_init__(self) -> None:
        if self.max_imprisonment_months is not None and self.max_imprisonment_months <= 0:
            raise ValueError("max_imprisonment_months must be positive or None")
        if self.harsher_than_imprisonment and self.max_imprisonment_months is None:
            raise ValueError("a sanction harsher than imprisonment must also contain imprisonment")


@dataclass(frozen=True)
class ImposedPunishment:
    """Punishment from the draft verdict. imprisonment_months None = milder than imprisonment."""

    imprisonment_months: int | None

    def __post_init__(self) -> None:
        if self.imprisonment_months is not None and self.imprisonment_months <= 0:
            raise ValueError("imprisonment_months must be positive or None")
